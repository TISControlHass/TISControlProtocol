from TISControlProtocol.Protocols import setup_udp_protocol
from TISControlProtocol.BytesHelper import build_packet
from homeassistant.core import HomeAssistant  # type: ignore
from homeassistant.components.http import HomeAssistantView  # type: ignore
from homeassistant.components import homeassistant  # type: ignore
from typing import Optional
from aiohttp import web  # type: ignore
import socket
import logging
from collections import defaultdict
import json
import asyncio
import ST7789
from PIL import Image
from PIL import ImageDraw  # noqa: F401
from PIL import ImageFont  # noqa: F401


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
        display_logo: Optional[str] = "./logo.png",
    ):
        """Initialize the API class."""
        self._host = host
        self._port = port
        self._local_ip = local_ip
        self._protocol = None
        self._transport = None
        self._hass = hass
        self._config_entries = {}
        self._domain = domain
        self._devices_dict = devices_dict
        self._display_logo = display_logo

    async def connect(self):
        """Connect to the TIS API."""
        try:
            self._hass.async_add_executor_job(self.run_display)
        except Exception as e:
            logging.error(f"error initializing display, {e}")
        self.loop = self._hass.loop
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self._transport, self._protocol = await setup_udp_protocol(
                self._sock,
                self.loop,
                self._host,
                self._port,
                self._local_ip,
                self._hass,
            )
            logging.error(
                f"Connected to TIS API successfully, ip_comport:{self._host},local:{self._local_ip}"
            )
        except Exception as e:
            logging.error(f"Error connecting to TIS API: {e}")

    def run_display(self, style="dots"):
        try:
            disp = ST7789.ST7789(
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
            disp.begin()
        except Exception as e:
            logging.error(f"error initializing display, {e}")
            return

        if self._display_logo:
            img = Image.open(self._display_logo)
        else:
            img = Image.open("./logo.png")
        disp.set_backlight(0)
        # reset display
        disp.display(img)

    async def _parse_device_manager_request(self, data: dict) -> None:
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
            if details[0]["gateway"] == self._host
        }

        grouped = defaultdict(list)
        for appliance, details in converted.items():
            if (
                details["appliance_type"]
                in self._hass.data[self._domain]["supported_platforms"]
            ):
                logging.error(f"appliance: {appliance}, details: {details}")
                grouped[details["appliance_type"]].append({appliance: details})

        self._config_entries = dict(grouped)
        # add a lock module config entry
        self._config_entries["lock_module"] = {
            "password": data["configs"]["lock_module_password"]
        }
        logging.error(f"config_entries stored: {self._config_entries}")
        # await self.update_entities()

    async def get_entities(self):
        """Get the entities."""
        try:
            with open("appliance_data.json", "r") as f:
                data = json.load(f)
                await self._parse_device_manager_request(data)
                logging.error(f"Data loaded from file: {data}")
        except Exception as e:
            # handle or log the exception
            logging.error(f"Error loading data from file: {e},file: {data}")
        await self._parse_device_manager_request(data)
        return self._config_entries


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
        # reload the platforms
        for entry in self.api._hass.config_entries.async_entries(self.api._domain):
            await self.api._hass.config_entries.async_reload(entry.entry_id)
        await self.api._hass.services.async_call(
            self.api._domain, homeassistant.SERVICE_RELOAD_ALL
        )


class ScanDevicesEndPoint(HomeAssistantView):
    """Scan Devices API endpoint."""

    url = "/api/scan_devices"
    name = "api:scan_devices"
    requires_auth = False

    def __init__(self, tis_api: TISApi):
        """Initialize the API endpoint."""
        self.api = tis_api
        self._discovery_packet = build_packet(
            operation_code=[0x00, 0x0E],
            ip_address=self.api._host,
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
                "device_type": self.api._devices_dict.get(
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
        self.api._hass.data[self.api._domain]["discovered_devices"] = []
        for i in range(prodcast_attempts):
            await self.api._protocol.sender.brodcast_packet(self._discovery_packet)
            # sleep for 1 sec
            await asyncio.sleep(1)

        return self.api._hass.data[self.api._domain]["discovered_devices"]
