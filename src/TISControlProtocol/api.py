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
from aiohttp import web
import socket
import logging
from collections import defaultdict
import json
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

        self.hass.data[self.domain]["discovered_devices"] = []
        self.hass.http.register_view(TISEndPoint(self))
        self.hass.http.register_view(ScanDevicesEndPoint(self))
        self.hass.http.register_view(GetKeyEndpoint(self))

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
        directroy = "/conf/data"
        os.makedirs(directroy, exist_ok=True)
        file_name = 'app.json'
        output_file = os.path.join(directroy, file_name)

        env_filename = '.env'
        env_file_path = os.path.join(directroy, env_filename)

        key = None
        load_dotenv(env_file_path)
        key = os.getenv("ENCRYPTION_KEY")

        if key is None:
            key = Fernet.generate_key().decode()
            try:
                with open(env_file_path, "w") as file:
                    file.write(f'ENCRYPTION_KEY="{key}"\n')
            except Exception as e:
                logging.error(f"Error writing .env file: {e}")
        try:
            with open(output_file, "r") as f:
                encrypted_str = json.load(f)
                decrypted_str = Fernet(key).decrypt(base64.b64decode(encrypted_str)).decode()
                data = json.loads(decrypted_str)
                await self.parse_device_manager_request(data)
        except FileNotFoundError:
            with open(output_file, "w") as f:
                json.dump('', f)
                data = {}
        await self.parse_device_manager_request(data)
        entities = self.config_entries.get(platform, [])
        return entities


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
        os.makedirs(directory, exist_ok=True)
        file_name = 'app.json'
        output_file = os.path.join(directory, file_name)

        env_filename = '.env'
        env_file_path = os.path.join(directory, env_filename)

        key = None
        load_dotenv(env_file_path)
        key = os.getenv("ENCRYPTION_KEY")

        if key is None:
            key = Fernet.generate_key().decode()
            try:
                with open(env_file_path, "w") as file:
                    file.write(f'ENCRYPTION_KEY="{key}"\n')
            except Exception as e:
                logging.error(f"Error writing .env file: {e}")

        # Parse the JSON data from the request
        data = await request.json()

        encrypted = Fernet(key).encrypt(json.dumps(data).encode())

        # Convert to base64 string
        encrypted_str = base64.b64encode(encrypted).decode()

        # Dump to file
        with open(output_file, "w") as f:
            json.dump(encrypted_str, f, indent=4)

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
        # TODO: some processing and formating
        return web.json_response(devices)

    async def discover_network_devices(self, prodcast_attempts=30) -> list:
        # empty current discovered devices list
        self.api.hass.data[self.api.domain]["discovered_devices"] = []
        for i in range(prodcast_attempts):
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

