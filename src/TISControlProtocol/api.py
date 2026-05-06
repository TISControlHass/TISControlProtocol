import json
import logging
import os
import socket
from collections import defaultdict
from datetime import timedelta
from typing import Optional

import aiofiles
import aiohttp
import psutil
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval
from PIL import Image, ImageDraw, ImageFont

from TISControlProtocol.Protocols import setup_udp_protocol
from TISControlProtocol.shared import get_real_mac

from .apis import (
    BillConfigEndpoint,
    ChangeSecurityPassEndpoint,
    GetBillConfigEndpoint,
    GetKeyEndpoint,
    PasswordsEndpoint,
    RestartEndpoint,
    ScanDevicesEndPoint,
    SubmitPasswordEndpoint,
    TISEndPoint,
    UpdateEndpoint,
    setup_views,
)

try:
    import time
    import spidev
    import gpiod
    from gpiod.line import Direction, Value

    HAS_ST7789 = True
except (ImportError, RuntimeError) as e:
    HAS_ST7789 = False
    logging.error(
        "Failed to load display dependencies. Display will be disabled. Error: %s", e
    )


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
        self._cms_task_unsub = None

    async def connect(self):
        """Connect to the TIS API."""
        self.loop = self.hass.loop
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            await self._setup_udp_protocol()
            await self._initialize_hass_data()
            await self._register_http_views()
            self.hass.async_add_executor_job(self.run_display)
            # self._register_services()
            # self._schedule_cms_data_task()
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
            await setup_views(self.hass)
            self.hass.http.register_view(TISEndPoint(self))
            self.hass.http.register_view(SubmitPasswordEndpoint(self))
            self.hass.http.register_view(ScanDevicesEndPoint(self))
            self.hass.http.register_view(GetKeyEndpoint(self))
            self.hass.http.register_view(ChangeSecurityPassEndpoint(self))
            self.hass.http.register_view(RestartEndpoint(self))
            self.hass.http.register_view(UpdateEndpoint(self))
            self.hass.http.register_view(BillConfigEndpoint(self))
            self.hass.http.register_view(GetBillConfigEndpoint(self))
            self.hass.http.register_view(PasswordsEndpoint(self))
        except Exception as e:
            logging.error("Error registering views %s", e)
            raise ConnectionError

    def _register_services(self):
        """Register Home Assistant services."""
        if self.hass.services.has_service(self.domain, "send_cms_data"):
            return

        logging.info("Registering CMS data service")

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

        if getattr(self, "_cms_task_unsub", None):
            self._cms_task_unsub()

        interval = timedelta(minutes=3)
        self._cms_task_unsub = async_track_time_interval(
            self.hass, scheduled_task, interval
        )

    def _unregister_cms_services(self):
        """Unregister CMS service and stop periodic task."""
        if self.hass.services.has_service(self.domain, "send_cms_data"):
            self.hass.services.async_remove(self.domain, "send_cms_data")

        logging.info("CMS data service unregistered")

        if getattr(self, "_cms_task_unsub", None):
            self._cms_task_unsub()
            self._cms_task_unsub = None

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

    def send_command(self, cmd):
        self.gpio_request.set_value(23, Value.INACTIVE) # Command mode (0)
        self.spi.xfer2([cmd])

    def send_data(self, data):
        self.gpio_request.set_value(23, Value.ACTIVE) # Data mode (1)
        self.spi.xfer2(list(data))

    def init_display(self):
        # Hardware Reset
        self.gpio_request.set_value(25, Value.INACTIVE)
        time.sleep(0.1)
        self.gpio_request.set_value(25, Value.ACTIVE)
        time.sleep(0.1)

        # ST7789 Initialization Sequence
        self.send_command(0x11) # Sleep out
        time.sleep(0.12)

        self.send_command(0x3A) # Color mode 16-bit
        self.send_data([0x55]) # 0x55 for RGB565

        self.send_command(0x36) # Memory Access Control (MADCTL)
        self.send_data([0x00]) # Normal rotation

        self.send_command(0x29) # Display on
        time.sleep(0.1)

    def set_window(self, x1, y1, x2, y2):
        self.send_command(0x2A) # Column Address Set
        self.send_data([x1 >> 8, x1 & 0xFF, x2 >> 8, x2 & 0xFF])

        self.send_command(0x2B) # Row Address Set
        self.send_data([y1 >> 8, y1 & 0xFF, y2 >> 8, y2 & 0xFF])

    def run_display(self, style="dots"):
        try:
            if HAS_ST7789:
                # Initialize SPI Bus
                self.spi = spidev.SpiDev()
                self.spi.open(0, 0)
                self.spi.max_speed_hz = 30 * 1000 * 1000  # 30 MHz (conservative and stable)
                self.spi.mode = 0b00

                # Open and request GPIO lines using gpiod v2 API
                self.gpio_request = gpiod.request_lines(
                    "/dev/gpiochip0",
                    consumer="display",
                    config={
                        23: gpiod.LineSettings(direction=Direction.OUTPUT, output_value=Value.INACTIVE),
                        25: gpiod.LineSettings(direction=Direction.OUTPUT, output_value=Value.ACTIVE),
                        12: gpiod.LineSettings(direction=Direction.OUTPUT, output_value=Value.ACTIVE),
                    },
                )

                self.init_display()
                self.set_display_image()
            else:
                logging.error("Can't start display, some packages are missing")

        except Exception as e:
            logging.error(f"error initializing display, {e}")
            return

    def set_display_image(self):
        if self.display_logo:
            img = Image.open(self.display_logo).convert("RGB")
            version_text = f"V {self.version}"

            draw = ImageDraw.Draw(img)
            try:
                font = ImageFont.load_default(size=28)
            except TypeError:
                font = ImageFont.load_default()
            
            x, y = 78, 235
            draw.text((x, y), version_text, font=font, fill=(255, 255, 255))
            img = img.rotate(-90, expand=True)

            # Convert image to RGB565 (16-bit)
            img_bytes = []
            for y in range(img.height):
                for x in range(img.width):
                    r, g, b = img.getpixel((x, y))
                    # Pack into RGB565 format
                    rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
                    img_bytes.append((rgb565 >> 8) & 0xFF)
                    img_bytes.append(rgb565 & 0xFF)

            # Send pixel data
            self.set_window(0, 0, img.width - 1, img.height - 1)
            self.send_command(0x2C) # Memory Write

            # Send in chunks to avoid overwhelming the SPI buffer
            chunk_size = 4096
            for i in range(0, len(img_bytes), chunk_size):
                chunk = img_bytes[i:i + chunk_size]
                self.gpio_request.set_value(23, Value.ACTIVE) # Data mode
                self.spi.xfer2(chunk)

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

        self.config_entries["passwords"] = data.get("passwords", {})
        self.config_entries["cms"] = bool(data["configs"].get("cms_send_data", False))
        if self.config_entries["cms"]:
            self._register_services()
            self._schedule_cms_data_task()
        else:
            self._unregister_cms_services()
        return self.config_entries

    async def get_entities(self, platform: str | None = None) -> list:
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
        logging.info(f"file (to be saved) length: {len(encrypted_data)}")

        async with aiofiles.open(output_file, "w") as f:
            logging.info("new appliances are getting saved in app.json")
            await f.write(json.dumps(encrypted_data, indent=4))

        logging.info("new appliances saved successfully")

    async def save_passwords(self, passwords):
        directory = "/config/custom_components/tis_integration/"
        os.makedirs(directory, exist_ok=True)

        data = await self.read_appliances(directory)
        data["passwords"] = passwords
        await self.save_appliances(data, directory)

    async def get_passwords(self):
        return await self.get_entities("passwords")

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
