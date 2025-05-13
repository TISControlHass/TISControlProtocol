from TISControlProtocol.Protocols import setup_udp_protocol
from TISControlProtocol.Protocols.udp.ProtocolHandler import (
    TISProtocolHandler,
    TISPacket,
)

import base64
from cryptography.fernet import Fernet
import os
from homeassistant.core import HomeAssistant  # type: ignore
from homeassistant.components.http import HomeAssistantView  # type: ignore
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
from PIL import Image
import uuid
from dotenv import load_dotenv


protocol_handler = TISProtocolHandler()


class TISApi:
    """TIS API class."""

    def __init__(
        self,
        port: int,
        hass: HomeAssistant,
        domain: str,
        devices_dict: dict,
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
        self.domain = domain
        self.devices_dict = devices_dict
        self.display_logo = display_logo
        self.display = None
        self.cms_url = "http://192.168.1.23"

    async def connect(self):
        """Connect to the TIS API."""
        self.loop = self.hass.loop
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
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

        try:
            self.hass.data[self.domain]["discovered_devices"] = []
            self.hass.http.register_view(TISEndPoint(self))
            self.hass.http.register_view(ScanDevicesEndPoint(self))
            self.hass.http.register_view(GetKeyEndpoint(self))
            self.hass.http.register_view(ChangeSecurityPassEndpoint(self))
            self.hass.http.register_view(
                CMSEndpoint(external_url=f"{self.cms_url}/api/device-health", api=self)
            )
            self.hass.async_add_executor_job(self.run_display)

            async def handle_cms_data(call):
                logging.warning(f"Starting CMS data sender \n call: {call}")
                cms_sender = CMSDataSender(
                    external_url=f"{self.cms_url}/api/device-health", hass=self.hass
                )
                cms_sender.send_data()

            self.hass.services.async_register(
                self.domain,
                "send_cms_data",
                handle_cms_data,
            )
        except ConnectionError as e:
            logging.error("Error registering views %s", e)
            raise ConnectionError

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
            img = Image.open(self.display_logo)
            self.display.set_backlight(0)
            # reset display
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
        directory = "/conf/data"
        os.makedirs(directory, exist_ok=True)

        key = await self.get_encryption_key(directory)
        data = await self.read_and_decrypt_data(directory, key)

        await self.parse_device_manager_request(data)
        entities = self.config_entries.get(platform, [])
        return entities

    async def get_encryption_key(self, directory: str) -> str:
        """Retrieve or generate the encryption key."""
        env_filename = ".env"
        env_file_path = os.path.join(directory, env_filename)

        await self.hass.async_add_executor_job(load_dotenv, env_file_path)
        key = os.getenv("ENCRYPTION_KEY")

        if key is None:
            key = Fernet.generate_key().decode()
            try:
                async with aiofiles.open(env_file_path, "w") as file:
                    await file.write(f'ENCRYPTION_KEY="{key}"\n')
            except Exception as e:
                logging.error(f"Error writing .env file: {e}")
        return key

    async def read_and_decrypt_data(self, directory: str, key: str) -> dict:
        """Read and decrypt the stored data."""
        file_name = "app.json"
        output_file = os.path.join(directory, file_name)

        try:
            async with aiofiles.open(output_file, "r") as f:
                encrypted_str = json.loads(await f.read())
                decrypted_str = (
                    Fernet(key).decrypt(base64.b64decode(encrypted_str)).decode()
                )
                data = json.loads(decrypted_str)
        except FileNotFoundError:
            async with aiofiles.open(output_file, "w") as f:
                await f.write(json.dumps(""))
                data = {}
        return data

    async def encrypt_and_save_data(self, data: dict, directory: str, key: str) -> None:
        """Encrypt and save the data."""
        file_name = "app.json"
        output_file = os.path.join(directory, file_name)

        encrypted = Fernet(key).encrypt(json.dumps(data).encode())
        encrypted_str = base64.b64encode(encrypted).decode()

        async with aiofiles.open(output_file, "w") as f:
            await f.write(json.dumps(encrypted_str, indent=4))


class TISEndPoint(HomeAssistantView):
    """TIS API endpoint."""

    url = "/api/tis"
    name = "api:tis"
    requires_auth = False

    def __init__(self, tis_api: TISApi):
        """Initialize the API endpoint."""
        self.api = tis_api

    async def post(self, request):
        directory = "/conf/data"
        key = await self.api.get_encryption_key(directory)

        # Parse the JSON data from the request
        data = await request.json()
        await self.api.encrypt_and_save_data(data, directory, key)

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
        mac = uuid.getnode()
        mac_address = ":".join(("%012X" % mac)[i : i + 2] for i in range(0, 12, 2))

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

        directory = "/conf/data"
        key = await self.tis_api.get_encryption_key(directory)
        data = await self.tis_api.read_and_decrypt_data(directory=directory, key=key)
        data["configs"]["lock_module_password"] = new_pass
        await self.tis_api.encrypt_and_save_data(data, directory, key)
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


class CMSDataSender:
    """CMS Data class."""

    def __init__(self, external_url: str, hass: HomeAssistant) -> None:
        self.external_url = external_url
        self.hass = hass

    async def get_data(self):
        try:
            # Mac Address Stuff
            mac = uuid.getnode()
            mac_address = ":".join(("%012X" % mac)[i : i + 2] for i in range(0, 12, 2))
            logging.warning(f"MAC Address: {mac_address}")

            # CPU Stuff
            cpu_usage = await self.hass.async_add_executor_job(psutil.cpu_percent, 1)
            logging.warning(f"CPU Usage: {cpu_usage}%")

            cpu_temp = await self.hass.async_add_executor_job(
                psutil.sensors_temperatures
            )
            logging.warning(f"Raw CPU Temperature Data: {cpu_temp}")
            cpu_temp = cpu_temp.get("cpu_thermal", None)
            if cpu_temp is not None:
                cpu_temp = cpu_temp[0].current
            else:
                cpu_temp = 0
            logging.warning(f"CPU Temperature: {cpu_temp}°C")

            # Disk Stuff
            total, used, free, percent = await self.hass.async_add_executor_job(
                psutil.disk_usage, "/"
            )
            logging.warning(
                f"Disk Usage - Total: {total}, Used: {used}, Free: {free}, Percent: {percent}%"
            )

            # Memory Stuff
            mem = await self.hass.async_add_executor_job(psutil.virtual_memory)
            logging.warning(
                f"Memory Usage - Total: {mem.total}, Free: {mem.free}, Percent: {mem.percent}%"
            )

            data = {
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
            logging.warning(f"Data to be sent to CMS: {data}")

            return data

        except Exception as e:
            logging.error(f"Error getting data for CMS: {e}")
            return None

    async def send_data(self):
        data = self.get_data()
        if data is not None:
            try:
                session = self.hass.helpers.aiohttp_client.async_get_clientsession()
                logging.warning(f"external url {self.external_url}")
                logging.warning(f"session: {session}")
                async with session.post(self.external_url, json=data) as response:
                    logging.warning(f"CMS Response Status: {response.status}")
                    if response.status != 200:
                        error_text = await response.text()
                        logging.error(f"Error sending data to CMS: {response.status}")
                        logging.error(f"Error response: {error_text}")
                        return False
                    else:
                        logging.info("Data sent to CMS successfully")
                        return True
            except aiohttp.ClientError as e:
                logging.error(f"ClientError while sending data to CMS: {e}")
                return False

        return False


class CMSEndpoint(HomeAssistantView):
    """Send data to CMS for monitoring."""

    url = "/api/cms"
    name = "api:cms"
    requires_auth = False

    def __init__(self, external_url, api: TISApi) -> None:
        """Initialize the endpoint."""
        self.api = api
        self.external_url = external_url

    async def get(self, request):
        try:
            logging.warning("Starting CMSEndpoint GET request processing")

            # Mac Address Stuff
            mac = uuid.getnode()
            mac_address = ":".join(("%012X" % mac)[i : i + 2] for i in range(0, 12, 2))
            logging.warning(f"MAC Address: {mac_address}")

            # CPU Stuff
            cpu_usage = await self.api.hass.async_add_executor_job(
                psutil.cpu_percent, 1
            )
            logging.warning(f"CPU Usage: {cpu_usage}%")

            cpu_temp = await self.api.hass.async_add_executor_job(
                psutil.sensors_temperatures
            )
            logging.warning(f"Raw CPU Temperature Data: {cpu_temp}")
            cpu_temp = cpu_temp.get("cpu_thermal", None)
            if cpu_temp is not None:
                cpu_temp = cpu_temp[0].current
            else:
                cpu_temp = 0
            logging.warning(f"CPU Temperature: {cpu_temp}°C")

            # Disk Stuff
            total, used, free, percent = await self.api.hass.async_add_executor_job(
                psutil.disk_usage, "/"
            )
            logging.warning(
                f"Disk Usage - Total: {total}, Used: {used}, Free: {free}, Percent: {percent}%"
            )

            # Memory Stuff
            mem = await self.api.hass.async_add_executor_job(psutil.virtual_memory)
            logging.warning(
                f"Memory Usage - Total: {mem.total}, Free: {mem.free}, Percent: {mem.percent}%"
            )

            data = {
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
            logging.warning(f"Data to be sent to CMS: {data}")

            session = self.api.hass.helpers.aiohttp_client.async_get_clientsession()
            logging.warning(f"external url {self.external_url}")
            logging.warning(f"session: {session}")
            try:
                async with session.post(self.external_url, json=data) as response:
                    logging.warning(f"CMS Response Status: {response.status}")
                    if response.status != 200:
                        error_text = await response.text()
                        logging.error(f"Error sending data to CMS: {response.status}")
                        logging.error(f"Error response: {error_text}")
                        return web.json_response(
                            {"error": "Error sending data to CMS"}, status=500
                        )
                    else:
                        logging.info("Data sent to CMS successfully")
                        return web.json_response(
                            {"message": "Data sent to CMS successfully"}
                        )
            except aiohttp.ClientError as e:
                logging.error(f"ClientError while sending data to CMS: {e}")
                return web.json_response(
                    {"error": "Error sending data to CMS"}, status=500
                )
        except Exception as e:
            logging.error(f"Unexpected error in CMSEndpoint: {e}", exc_info=True)
            return web.json_response(
                {"error": "Error in CMSEndpoint", "message": str(e)}, status=500
            )
