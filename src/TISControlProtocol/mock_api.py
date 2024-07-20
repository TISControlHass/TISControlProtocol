from TISControlProtocol.Protocols import setup_udp_protocol
from TISControlProtocol.BytesHelper import build_packet
from homeassistant.core import HomeAssistant  # type: ignore
from homeassistant.components.http import HomeAssistantView  # type: ignore
from typing import Optional
from aiohttp import web  # type: ignore
import socket
import logging
from collections import defaultdict
import json
import asyncio
from PIL import Image, ImageDraw, ImageFont  # noqa: F401


class TISApi:
    """TIS API class."""

    def __init__(
        self,
        host: str,
        port: int,
        local_ip: str,
        hass: HomeAssistant,
        domain: str,
        devices_dict: dict,
        display_logo: Optional[str] = "./custom_components/tis_control/shakalpng.png",
    ):
        """Initialize the API class."""
        self.host = host
        self.port = port
        self.local_ip = local_ip
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
                self.local_ip,
                self.hass,
            )
            logging.info(
                f"Connected to TIS API successfully, ip_comport:{self.host},local:{self.local_ip}"
            )
        except Exception as e:
            logging.error("Error connecting to TIS API %s", e)
        self.hass.http.register_view(TISEndPoint(self))
        self.hass.http.register_view(ScanDevicesEndPoint(self))

    def run_display(self, style="dots"):
        try:
            self.display = FakeDisplay()
            # Initialize display.
            self.display.begin()
            self.set_display_image()

        except Exception as e:
            logging.error(f"error initializing display, {e}")
            return

    def set_display_image(self):
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
                        "channel_type": detail["channel_type"],
                        "channel_name": detail["channel_name"],
                    }
                    for detail in details
                ],
            }
            for appliance, details in data["appliances"].items()
        }

        grouped = defaultdict(list)
        for appliance, details in converted.items():
            if (
                details["appliance_type"]
                in self.hass.data[self.domain]["supported_platforms"]
            ):
                grouped[details["appliance_type"]].append({appliance: details})

        self.config_entries = dict(grouped)
        # add a lock module config entry
        self.config_entries["lock_module"] = {
            "password": data["configs"]["lock_module_password"]
        }
        # return response
        return self.config_entries
        # await self.update_entities()

    async def get_entities(self, platform: str = None):
        """Get the stored entities."""
        try:
            with open("appliance_data.json", "r") as f:
                data = json.load(f)
                await self.parse_device_manager_request(data)
        except FileNotFoundError:
            with open("appliance_data.json", "w") as f:
                pass
        await self.parse_device_manager_request(data)
        return self.config_entries[platform]


class TISEndPoint(HomeAssistantView):
    """TIS API endpoint."""

    url = "/api/tis"
    name = "api:tis"
    requires_auth = False

    def __init__(self, tis_api: TISApi):
        """Initialize the API endpoint."""
        self.api = tis_api

    async def post(self, request):
        # Parse the JSON data from the request
        data = await request.json()
        # dump to file
        with open("appliance_data.json", "w") as f:
            json.dump(data, f, indent=4)

        # Start reload operations in the background
        asyncio.create_task(self.reload_platforms())

        # Return the response immediately
        return web.json_response({"message": "success"})

    async def reload_platforms(self):
        # Reload the platforms
        for entry in self.api.hass.config_entries.async_entries(self.api.domain):
            await self.api.hass.config_entries.async_reload(entry.entry_id)

        # await self.api.hass.services.async_call(
        #     self.api.domain, homeassistant.SERVICE_RELOAD_ALL
        # )


class ScanDevicesEndPoint(HomeAssistantView):
    """Scan Devices API endpoint."""

    url = "/api/scan_devices"
    name = "api:scan_devices"
    requires_auth = False

    def __init__(self, tis_api: TISApi):
        """Initialize the API endpoint."""
        self.api = tis_api
        self.discovery_packet = build_packet(
            operation_code=[0x00, 0x0E],
            ip_address=self.api.host,
            destination_mac="FF:FF:FF:FF:FF:FF",
            device_id=[0xFF, 0xFF],
            additional_packets=[],
        )

    async def get(self, request):
        # Discover network devices
        devices = await self.discover_network_devices()
        devices = [
            {
                "device_id": device["device_id"],
                "device_type": self.api.devices_dict.get(
                    tuple(device["device_type"]), tuple(device["device_type"])
                ),
                "gateway": device["source_ip"],
            }
            for device in devices
        ]
        # TODO: some processing and formating
        return web.json_response(devices)

    async def discover_network_devices(self, prodcast_attempts=10) -> list:
        # empty current discovered devices list
        self.api.hass.data[self.api.domain]["discovered_devices"] = []
        for i in range(prodcast_attempts):
            await self.api.protocol.sender.brodcast_packet(self.discovery_packet)
            # sleep for 1 sec
            await asyncio.sleep(1)

        return self.api.hass.data[self.api.domain]["discovered_devices"]


class FakeDisplay:
    def __init__(self):
        pass

    def begin(self):
        pass

    def set_backlight(self, value):
        pass

    def display(self, img):
        pass
