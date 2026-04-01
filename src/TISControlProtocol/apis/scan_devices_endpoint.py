import asyncio
import ipaddress

from aiohttp import web
from homeassistant.components.http import HomeAssistantView

from TISControlProtocol.Protocols.udp.ProtocolHandler import (
    TISPacket,
    TISProtocolHandler,
)

protocol_handler = TISProtocolHandler()


class ScanDevicesEndPoint(HomeAssistantView):
    """Scan Devices API endpoint."""

    url = "/api/scan_devices"
    name = "api:scan_devices"
    requires_auth = False

    def __init__(self, tis_api):
        """Initialize the API endpoint."""
        self.api = tis_api
        self.discovery_packet: TISPacket = protocol_handler.generate_discovery_packet()

    async def get(self, request):
        remote_ip = ipaddress.ip_address(request.remote)
        is_local = remote_ip.is_private or remote_ip.is_loopback

        if not is_local:
            return web.json_response(
                {"error": "Unauthorized: Local network access only"}, status=403
            )

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
