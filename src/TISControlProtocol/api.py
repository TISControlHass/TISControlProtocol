from TISControlProtocol.Protocols import setup_udp_protocol
from TISControlProtocol.Protocols.udp.ProtocolHandler import (
    TISProtocolHandler,
    TISPacket,
)

import os
from datetime import timedelta
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.core import HomeAssistant
from homeassistant.components.http import HomeAssistantView
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from typing import Optional
import aiohttp
from aiohttp import web
import aiofiles
import socket
import logging
from collections import defaultdict
import json
import psutil
import asyncio
import ST7789
from PIL import Image, ImageDraw, ImageFont
from TISControlProtocol.shared import get_real_mac

protocol_handler = TISProtocolHandler()


class TISApi:
    """TIS API class."""

    def __init__(
        self,
        port: int,
        hass: HomeAssistant,
        domain: str,
        devices_dict: dict,
        version: str,
        host: str = "0.0.0.0",
        display_logo: Optional[str] = None,
    ):
        """Initialize the API class."""
        self.host = host
        self.port = port
        self.protocol = None
        self.transport = None
        self.hass = hass
        self.config_entries = {}
        self.bill_configs = {}
        self.domain = domain
        self.devices_dict = devices_dict
        self.display_logo = display_logo
        self.display = None
        self.version = version
        self.cms_url = "https://cms-tis.com"

    async def connect(self):
        """Connect to the TIS API."""
        self.loop = self.hass.loop
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            await self._setup_udp_protocol()
            await self._initialize_hass_data()
            await self._register_http_views()
            self.hass.async_add_executor_job(self.run_display)
            self._register_services()
            self._schedule_cms_data_task()
        except Exception as e:
            logging.error("Error during connection setup: %s", e)
            raise ConnectionError

    async def _setup_udp_protocol(self):
        """Setup the UDP protocol."""
        try:
            self.transport, self.protocol = await setup_udp_protocol(
                self.sock,
                self.loop,
                self.host,
                self.port,
                self.hass,
            )
        except Exception as e:
            logging.error("Error connecting to TIS API %s", e)
            raise ConnectionError

    async def _initialize_hass_data(self):
        """Initialize Home Assistant data."""
        self.hass.data[self.domain]["discovered_devices"] = []

    async def _register_http_views(self):
        """Register HTTP views."""
        try:
            self.hass.http.register_view(TISEndPoint(self))
            self.hass.http.register_view(ScanDevicesEndPoint(self))
            self.hass.http.register_view(GetKeyEndpoint(self))
            self.hass.http.register_view(ChangeSecurityPassEndpoint(self))
            self.hass.http.register_view(RestartEndpoint(self))
            self.hass.http.register_view(UpdateEndpoint(self))
            self.hass.http.register_view(BillConfigEndpoint(self))
            self.hass.http.register_view(GetBillConfigEndpoint(self))
        except Exception as e:
            logging.error("Error registering views %s", e)
            raise ConnectionError

    def _register_services(self):
        """Register Home Assistant services."""

        async def handle_cms_data(call):
            data = call.data.get("data", None)

            if data is None:
                logging.error("No data provided to send to CMS")
                return

            cms_sender = CMSDataSender(
                external_url=f"{self.cms_url}/api/device-health",
                hass=self.hass,
            )
            await cms_sender.send_data(data)

        self.hass.services.async_register(
            self.domain,
            "send_cms_data",
            handle_cms_data,
        )

    def _schedule_cms_data_task(self):
        """Schedule periodic CMS data task."""

        async def scheduled_task(now=None):
            try:
                data = await self._collect_system_data()

                await self.hass.services.async_call(
                    self.domain,
                    "send_cms_data",
                    {"data": data},
                )
            except Exception as e:
                logging.error(f"Error getting data for CMS: {e}")

        interval = timedelta(minutes=3)
        async_track_time_interval(self.hass, scheduled_task, interval)

    async def _collect_system_data(self):
        """Collect system data for CMS."""
        # Mac Address
        mac_address = await get_real_mac("end0")

        # CPU Usage
        cpu_usage = await self.hass.async_add_executor_job(psutil.cpu_percent, 1)

        # CPU Temperature
        cpu_temp = await self.hass.async_add_executor_job(psutil.sensors_temperatures)
        cpu_temp = cpu_temp.get("cpu_thermal", None)
        cpu_temp = cpu_temp[0].current if cpu_temp else 0

        # Disk Usage
        total, _, free, percent = await self.hass.async_add_executor_job(
            psutil.disk_usage, "/"
        )

        # Memory Usage
        mem = await self.hass.async_add_executor_job(psutil.virtual_memory)

        return {
            "mac_address": mac_address,
            "cpu_usage": cpu_usage,
            "cpu_temperature": cpu_temp,
            "disk_total": total,
            "disk_free": free,
            "disk_percent": percent,
            "ram_total": mem.total,
            "ram_free": mem.free,
            "ram_percent": mem.percent,
        }

    def run_display(self, style="dots"):
        try:
            self.display = ST7789.ST7789(
                width=320,
                height=240,
                rotation=0,
                port=0,
                cs=0,
                dc=23,
                rst=25,
                backlight=12,
                spi_speed_hz=60 * 1000 * 1000,
                offset_left=0,
                offset_top=0,
            )
            # Initialize display.
            self.display.begin()
            self.set_display_image()

        except Exception as e:
            logging.error(f"error initializing display, {e}")
            return

    def set_display_image(self):
        if self.display_logo:
            img = Image.open(self.display_logo).convert("RGB")
            version_text = f"V {self.version}"

            draw = ImageDraw.Draw(img)
            font = ImageFont.load_default(size=28)
            x, y = 78, 235
            draw.text((x, y), version_text, font=font, fill=(255, 255, 255))
            img = img.rotate(-90, expand=True)

            self.display.set_backlight(0)
            self.display.display(img)

    async def parse_device_manager_request(self, data: dict) -> None:
        """Parse the device manager request."""
        converted = {
            appliance: {
                "device_id": [int(n) for n in details[0]["device_id"].split(",")],
                "appliance_type": details[0]["appliance_type"]
                .lower()
                .replace(" ", "_"),
                "appliance_class": details[0].get("appliance_class", None),
                "is_protected": bool(int(details[0]["is_protected"])),
                "gateway": details[0]["gateway"],
                "channels": [
                    {
                        "channel_number": int(detail["channel_number"]),
                        "channel_name": detail["channel_name"],
                    }
                    for detail in details
                ],
                "min": details[0]["min"],
                "max": details[0]["max"],
                "settings": details[0]["settings"],
            }
            for appliance, details in data["appliances"].items()
        }

        grouped = defaultdict(list)
        for appliance, details in converted.items():
            grouped[details["appliance_type"]].append({appliance: details})
        self.config_entries = dict(grouped)

        # add a lock module config entry
        self.config_entries["lock_module"] = {
            "password": data["configs"]["lock_module_password"]
        }
        return self.config_entries

    async def get_entities(self, platform: str = None) -> list:
        """Get the stored entities."""
        directory = "/config/custom_components/tis_integration/"
        os.makedirs(directory, exist_ok=True)

        data = await self.read_appliances(directory)

        await self.parse_device_manager_request(data)
        entities = self.config_entries.get(platform, [])
        return entities

    async def read_appliances(self, directory: str) -> dict:
        """Read, decrypt, and return the stored data."""
        file_name = "app.json"
        output_file = os.path.join(directory, file_name)

        try:
            async with aiofiles.open(output_file, "r") as f:
                raw_data = await f.read()
                # logging.warning(f"file length: {len(raw_data)}")
                if raw_data:
                    encrypted_data = json.loads(raw_data)
                    data = self.decrypt_data(encrypted_data)
                else:
                    data = {}
        except FileNotFoundError:
            data = {}
        return data

    async def save_appliances(self, data: dict, directory: str) -> None:
        """Encrypt and save the data."""
        file_name = "app.json"
        output_file = os.path.join(directory, file_name)

        encrypted_data = self.encrypt_data(data)
        logging.warning(f"file (to be saved) length: {len(encrypted_data)}")

        async with aiofiles.open(output_file, "w") as f:
            logging.warning("new appliances are getting saved in app.json")
            await f.write(json.dumps(encrypted_data, indent=4))

        logging.warning("new applinaces saved successfully")

    async def get_bill_configs(self) -> dict:
        """Get Bill Configurations"""
        try:
            directory = "/config/custom_components/tis_integration/"
            os.makedirs(directory, exist_ok=True)

            file_name = "bill.json"
            output_file = os.path.join(directory, file_name)

            async with aiofiles.open(output_file, "r") as f:
                data = json.loads(await f.read())
        except FileNotFoundError:
            async with aiofiles.open(output_file, "w") as f:
                await f.write(json.dumps(""))
                data = {}
        self.bill_configs = data
        return data

    def encrypt(self, text: str, shift: int = 5) -> str:
        result = ""
        for char in text:
            if char.isalpha():
                base = ord("A") if char.isupper() else ord("a")
                result += chr((ord(char) - base + shift) % 26 + base)
            else:
                result += char
        return result

    def decrypt(self, text: str, shift: int = 5) -> str:
        return self.encrypt(text, -shift)

    def encrypt_data(self, data, shift: int = 5):
        if isinstance(data, dict):
            return {
                self.encrypt(str(k), shift): self.encrypt_data(v, shift)
                for k, v in data.items()
            }
        elif isinstance(data, list):
            return [self.encrypt_data(item, shift) for item in data]
        elif isinstance(data, str):
            return self.encrypt(data, shift)
        else:
            return data

    def decrypt_data(self, data, shift: int = 5):
        if isinstance(data, dict):
            return {
                self.decrypt(str(k), shift): self.decrypt_data(v, shift)
                for k, v in data.items()
            }
        elif isinstance(data, list):
            return [self.decrypt_data(item, shift) for item in data]
        elif isinstance(data, str):
            return self.decrypt(data, shift)
        else:
            return data


class TISEndPoint(HomeAssistantView):
    """TIS API endpoint."""

    url = "/api/tis"
    name = "api:tis"
    requires_auth = False

    def __init__(self, tis_api: TISApi):
        """Initialize the API endpoint."""
        self.api = tis_api

    async def post(self, request):
        directory = "/config/custom_components/tis_integration/"

        # Parse the JSON data from the request
        data = await request.json()
        await self.api.save_appliances(data, directory)

        # Start reload operations in the background
        asyncio.create_task(self.reload_platforms())

        # Return the response immediately
        return web.json_response({"message": "success"})

    async def reload_platforms(self):
        # Reload the platforms
        for entry in self.api.hass.config_entries.async_entries(self.api.domain):
            await self.api.hass.config_entries.async_reload(entry.entry_id)


class ScanDevicesEndPoint(HomeAssistantView):
    """Scan Devices API endpoint."""

    url = "/api/scan_devices"
    name = "api:scan_devices"
    requires_auth = False

    def __init__(self, tis_api: TISApi):
        """Initialize the API endpoint."""
        self.api = tis_api
        self.discovery_packet: TISPacket = protocol_handler.generate_discovery_packet()

    async def get(self, request):
        # Discover network devices
        devices = await self.discover_network_devices()
        devices = [
            {
                "device_id": device["device_id"],
                "device_type_code": device["device_type"],
                "device_type_name": self.api.devices_dict.get(
                    tuple(device["device_type"]), tuple(device["device_type"])
                ),
                "gateway": device["source_ip"],
            }
            for device in devices
        ]
        return web.json_response(devices)

    async def discover_network_devices(self, broadcast_attempts=30) -> list:
        # empty current discovered devices list
        self.api.hass.data[self.api.domain]["discovered_devices"] = []
        for i in range(broadcast_attempts):
            await self.api.protocol.sender.broadcast_packet(self.discovery_packet)
            # sleep for 1 sec
            await asyncio.sleep(1)

        return self.api.hass.data[self.api.domain]["discovered_devices"]


class GetKeyEndpoint(HomeAssistantView):
    """Get Key API endpoint."""

    url = "/api/get_key"
    name = "api:get_key"
    requires_auth = False

    def __init__(self, tis_api: TISApi):
        """Initialize the API endpoint."""
        self.api = tis_api

    async def get(self, request):
        # Get the MAC address
        mac_address = await get_real_mac("end0")
        if mac_address is None:
            return web.json_response(
                {"error": "Could not retrieve MAC address"}, status=500
            )

        # Return the MAC address
        return web.json_response({"key": mac_address})


class ChangeSecurityPassEndpoint(HomeAssistantView):
    """Change Security Password API Endpoint."""

    url = "/api/change_pass"
    name = "api:change_pass"
    requires_auth = False

    def __init__(self, tis_api: TISApi):
        self.tis_api = tis_api

    async def post(self, request):
        try:
            old_pass = request.query.get("old_pass")
            new_pass = request.query.get("new_pass")
            confirm_pass = request.query.get("confirm_pass")

            if old_pass is None or new_pass is None or confirm_pass is None:
                logging.info(
                    "Required parameters not found in query, parsing request body"
                )
                data = await request.json()
                old_pass = old_pass or data.get("old_pass")
                new_pass = new_pass or data.get("new_pass")
                confirm_pass = confirm_pass or data.get("confirm_pass")

            if old_pass is None or new_pass is None or confirm_pass is None:
                logging.error("Missing required parameters")
                return web.json_response(
                    {
                        "message": "error",
                        "error": "Missing required parameters",
                    },
                    status=400,
                )

        except Exception as e:
            logging.error(f"Error parsing request: {e}")
            return web.json_response(
                {"message": "error", "error": "Invalid request parameters"},
                status=400,
            )

        if old_pass != self.tis_api.config_entries["lock_module"]["password"]:
            return web.json_response(
                {
                    "message": "error",
                    "error": "Old password is incorrect, please try again",
                },
                status=403,
            )

        if new_pass == old_pass:
            return web.json_response(
                {
                    "message": "error",
                    "error": "New password must be different from the old password",
                },
                status=400,
            )

        if len(new_pass) < 4:
            return web.json_response(
                {
                    "message": "error",
                    "error": "Password must be at least 4 characters long",
                },
                status=400,
            )

        if new_pass != confirm_pass:
            return web.json_response(
                {
                    "message": "error",
                    "error": "New password and confirmation do not match",
                },
                status=400,
            )

        directory = "/config/custom_components/tis_integration/"
        data = await self.tis_api.read_appliances(directory=directory)
        data["configs"]["lock_module_password"] = new_pass
        await self.tis_api.save_appliances(data, directory)
        self.tis_api.config_entries["lock_module"]["password"] = new_pass

        asyncio.create_task(self.reload_platforms())

        return web.json_response(
            {
                "message": "success",
            }
        )

    async def reload_platforms(self):
        for entry in self.tis_api.hass.config_entries.async_entries(
            self.tis_api.domain
        ):
            await self.tis_api.hass.config_entries.async_reload(entry.entry_id)


class RestartEndpoint(HomeAssistantView):
    """Restart the Server"""

    url = "/api/restart"
    name = "api:restart"
    requires_auth = False

    def __init__(self, tis_api: TISApi):
        self.tis_api = tis_api

    async def post(self, request):
        mac_address = request.query.get("mac_address")

        if mac_address is None:
            logging.info("Required parameters not found in query, parsing request body")
            data = await request.json()
            mac_address = data.get("mac_address")

        mac = await get_real_mac("end0")

        if mac_address is None:
            return web.json_response(
                {"error": "required parameters are missing"}, status=400
            )
        elif mac_address != mac:
            return web.json_response({"error": "Unauthorized"}, status=403)

        logging.info("Restarting Server")
        try:
            await self.tis_api.hass.services.async_call(
                "homeassistant", "restart", {}, blocking=False
            )
            return web.json_response({"message": "Server is restarting"}, status=200)
        except Exception as e:
            logging.error(f"Error restarting server: {e}")
            return web.json_response({"error": "Failed to restart server"}, status=500)


class UpdateEndpoint(HomeAssistantView):
    """Update the Server"""

    url = "/api/update"
    name = "api:update"
    requires_auth = False

    def __init__(self, tis_api: TISApi):
        self.tis_api = tis_api

    async def post(self, request):
        mac_address = request.query.get("mac_address")

        if mac_address is None:
            logging.info("Required parameters not found in query, parsing request body")
            data = await request.json()
            mac_address = data.get("mac_address")

        mac = await get_real_mac("end0")

        if mac_address is None:
            return web.json_response(
                {"error": "required parameters are missing"}, status=400
            )
        elif mac_address != mac:
            return web.json_response({"error": "Unauthorized"}, status=403)

        try:
            integration_dir = self.tis_api.hass.config.path(
                "custom_components", "tis_integration"
            )

            async def run(cmd, cwd):
                """Run a shell command in cwd, return (exit_code, stdout, stderr)."""
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    cwd=cwd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                out, err = await proc.communicate()
                return proc.returncode, out.decode().strip(), err.decode().strip()

            results = {}
            name, path = ("integration", integration_dir)
            code, out, err = await run(["git", "reset", "--hard", "HEAD"], cwd=path)
            results[f"{name}_reset"] = {"code": code, "stdout": out, "stderr": err}
            if code != 0:
                logging.error("Reset %s failed: %s", name, err)
                return web.json_response(
                    {
                        "error": f"{name} reset failed",
                        "details": results[name + "_reset"],
                    },
                    status=500,
                )

            code, out, err = await run(["git", "pull"], cwd=path)
            results[f"{name}_pull"] = {"code": code, "stdout": out, "stderr": err}
            if code != 0:
                logging.error("Pull %s failed: %s", name, err)
                return web.json_response(
                    {
                        "error": f"{name} pull failed",
                        "details": results[name + "_pull"],
                    },
                    status=500,
                )

            logging.info("Successfully updated integration")
            return web.json_response(
                {
                    "message": "TIS integrations updated successfully",
                    "results": results,
                }
            )

        except Exception as e:
            logging.error(f"Could Not Update Server: {e}")
            return web.json_response({"error": "Failed to update server"}, status=500)


class BillConfigEndpoint(HomeAssistantView):
    """Save Bill Configurations"""

    url = "/api/bill-config"
    name = "api:bill-config"
    requires_auth = False

    def __init__(self, tis_api: TISApi):
        self.tis_api = tis_api

    async def post(self, request):
        try:
            data = await request.json()

            if not data or "summer_rates" not in data or "winter_rates" not in data:
                logging.error("Required parameters are missing in the request")
                return web.json_response(
                    {"error": "Required parameters are missing"}, status=400
                )

            directory = "/config/custom_components/tis_integration/"
            os.makedirs(directory, exist_ok=True)

            file_name = "bill.json"
            output_file = os.path.join(directory, file_name)

            async with aiofiles.open(output_file, "w") as f:
                await f.write(json.dumps(data, indent=4))

            self.tis_api.bill_configs = data

            # Start reload operations in the background
            asyncio.create_task(self.reload_platforms())

            # Return the response immediately
            return web.json_response({"message": "Bill config saved successfully"})
        except Exception as e:
            logging.error(f"Error saving bill config: {e}")
            return web.json_response(
                {"error": "Failed to save bill config"}, status=500
            )

    async def reload_platforms(self):
        # Reload the platforms
        for entry in self.api.hass.config_entries.async_entries(self.api.domain):
            await self.api.hass.config_entries.async_reload(entry.entry_id)


class GetBillConfigEndpoint(HomeAssistantView):
    """Get Bill Configurations"""

    url = "/api/get-bill-config"
    name = "api:get-bill-config"
    requires_auth = False

    def __init__(self, tis_api: TISApi):
        self.tis_api = tis_api

    async def post(self, request):
        try:
            if self.tis_api.bill_configs:
                configs = self.tis_api.bill_configs
            else:
                configs = await self.tis_api.get_bill_configs()

            logging.info(f"bill configs: {configs}")

            return web.json_response({"config": configs})
        except Exception as e:
            logging.error(f"Error getting bill config: {e}")
            return web.json_response({"error": "Failed to get bill config"}, status=500)


class CMSDataSender:
    """CMS Data class."""

    def __init__(self, external_url: str, hass: HomeAssistant) -> None:
        self.external_url = external_url
        self.hass = hass

    async def send_data(self, data):
        if data is not None:
            try:
                session = async_get_clientsession(self.hass)
                async with session.post(self.external_url, json=data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logging.warning(f"Error sending data to CMS: {response.status}")
                        logging.info(f"Error response: {error_text}")
                        return False
                    else:
                        logging.info("Data sent to CMS successfully")
                        return True
            except aiohttp.ClientError as e:
                logging.warning(f"ClientError while sending data to CMS: {e}")
                return False

        return False
