import asyncio
import ipaddress
import logging

from aiohttp import web
from homeassistant.components.http import HomeAssistantView

from TISControlProtocol.shared import get_real_mac

_LOGGER = logging.getLogger(__name__)


class TISEndPoint(HomeAssistantView):
    """TIS API endpoint."""

    url = "/api/tis"
    name = "api:tis"
    requires_auth = False

    def __init__(self, tis_api):
        """Initialize the API endpoint."""
        self.api = tis_api

    async def post(self, request):
        # 1. IP-based security check
        remote_ip = ipaddress.ip_address(request.remote)
        is_local = remote_ip.is_private or remote_ip.is_loopback

        if not is_local:
            return web.json_response(
                {"error": "Unauthorized: Local network access only"}, status=403
            )

        # 2. MAC Address validation
        # Try to get mac_address from query string first
        mac_address = request.query.get("mac_address")

        # Parse the JSON data from the request body
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"error": "Invalid JSON"}, status=400)

        # If not in query, check the body
        if mac_address is None:
            mac_address = data.get("mac_address")

        # Fetch local MAC for comparison
        local_mac = await get_real_mac("end0")

        if mac_address is None:
            return web.json_response({"error": "Unauthorized"}, status=403)

        # Compare provided MAC with the hardware MAC
        if mac_address.lower() != local_mac.lower():
            _LOGGER.warning("Unauthorized")
            return web.json_response({"error": "Unauthorized"}, status=403)

        # 3. Process the valid request
        directory = "/config/custom_components/tis_integration/"
        await self.api.save_appliances(data, directory)

        # Start reload operations in the background
        asyncio.create_task(self.reload_platforms())

        # Return the response immediately
        return web.json_response({"message": "success"})

    async def reload_platforms(self):
        """Reload the platforms."""
        for entry in self.api.hass.config_entries.async_entries(self.api.domain):
            await self.api.hass.config_entries.async_reload(entry.entry_id)
