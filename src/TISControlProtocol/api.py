import json
import logging
import os
import socket
from collections import defaultdict
from typing import Optional

import aiofiles
from homeassistant.core import HomeAssistant

from TISControlProtocol.Protocols import setup_udp_protocol

from .services import CMSService, ServiceManager

from .apis import (
    BillConfigEndpoint,
    ChangeSecurityPassEndpoint,
    ToggleConnectionEndpoint,
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
        self.loop = None
        self.protocol = None
        self.transport = None
        self.sock = None
        self.hass = hass
        self.config_entries = {}
        self.bill_configs = {}
        self.domain = domain
        self.devices_dict = devices_dict
        self.display_logo = display_logo
        self.display = None
        self.version = version
        self.cms_url = "https://cms-tis.com"
        self.service_manager = ServiceManager(self.hass, self.domain)
        self.service_manager.register(CMSService(self.hass, self.domain, self.cms_url))

    async def setup(self):
        """Setup the TIS API."""
        try:
            await self.connect()
            await self._initialize_hass_data()
            await self._register_http_views()
            self.hass.async_add_executor_job(self.run_display)
        except Exception as e:
            logging.error("Error during setup: %s", e)

    async def connect(self):
        """Connect to the TIS API."""
        self.loop = self.hass.loop
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        try:
            await self._setup_udp_protocol()
        except Exception:
            self.sock.close()
            self.sock = None
            self.loop = None
            raise

    async def disconnect(self):
        """Disconnect from the TIS API."""
        if self.transport:
            self.transport.close()
            self.transport = None
        self.protocol = None
        self.loop = None
        if hasattr(self, "sock") and self.sock:
            self.sock.close()
            self.sock = None

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
            self.hass.http.register_view(ToggleConnectionEndpoint(self))
        except Exception as e:
            logging.error("Error registering views %s", e)
            raise ConnectionError

    def run_display(self, style="dots"):
        from .display import TISDisplay

        if self.display is None:
            self.display = TISDisplay(self.display_logo, self.version)

        self.display.run_display()

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
        self.service_manager.toggle("cms", self.config_entries["cms"])

        self.config_entries["connected"] = bool(data["configs"].get("connected", True))
        if not self.config_entries["connected"]:
            await self.disconnect()
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
