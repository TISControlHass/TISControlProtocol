import asyncio
import logging
import socket

from homeassistant.core import HomeAssistant
from TISControlProtocol.Protocols import setup_udp_protocol
from TISControlProtocol.Protocols.udp.ProtocolHandler import (
    TISPacket,
    TISProtocolHandler,
)

from .DiscoveryHelpers import DEVICE_APPLIANCES

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
        self.discovery_packet: TISPacket = protocol_handler.generate_discovery_packet()

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

        # scan for devices
        await self.scan_devices()

    async def scan_devices(self, prodcast_attempts=10):
        """Scan for devices."""
        # clear the previous discovered devices
        self.hass.data[self.domain]["discovered_devices"] = []

        # send dicover packet
        for _ in range(prodcast_attempts):
            await self.protocol.sender.broadcast_packet(self.discovery_packet)
            await asyncio.sleep(1)

        # fetch the devices
        devices = [
            {
                "device_id": device["device_id"],
                "device_type_code": device["device_type"],
                "device_type_name": self.devices_dict.get(
                    tuple(device["device_type"]), tuple(device["device_type"])
                ),
                "gateway": ".".join(map(str, device["source_ip"])),
            }
            for device in self.hass.data[self.domain]["discovered_devices"]
        ]

        # save devices
        self.hass.data[self.domain]["devices"] = devices

    async def get_entities(self, platform: str):
        # load devices
        devices = self.hass.data[self.domain]["devices"]

        # parse devices
        appliances = self.parse_saved_devices(devices)
        logging.warning(
            f"appliances for platform {platform}: {appliances.get(platform, [])}"
        )

        # return appliances
        return appliances.get(platform, [])

    def parse_saved_devices(self, devices: list[dict]):
        """convert saved devices payload to usable format"""
        appliances = {}
        for device in devices:
            # get the device appliances
            device_appliances = DEVICE_APPLIANCES.get(
                tuple(device["device_type_code"]), None
            )
            if device_appliances:
                # itterate over the appliances
                for platform, count in device_appliances["appliances"].items():
                    # check if platform exists if not create key with empty list
                    if platform not in appliances:
                        appliances[platform] = []
                    for i in range(1, count + 1):
                        appliance = {
                            "name": f"{str(device['device_id'])} {platform} channel{i}",
                            "device_id": device["device_id"],
                            "device_type_name": device["device_type_name"],
                            "gateway": device["gateway"],
                            "channels": [
                                {
                                    "Output": i,
                                }
                            ],
                            "is_protected": False,
                        }
                        appliances[platform].append(appliance)
        return appliances
