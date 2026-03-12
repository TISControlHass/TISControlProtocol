import asyncio
import ipaddress

from aiohttp import web
from homeassistant.components.http import HomeAssistantView


class TISEndPoint(HomeAssistantView):
    """TIS API endpoint."""

    url = "/api/tis"
    name = "api:tis"
    requires_auth = False

    def __init__(self, tis_api):
        """Initialize the API endpoint."""
        self.api = tis_api

    async def post(self, request):
        # 1. Get the real remote IP
        # request.remote usually gives the immediate connection (the Cloudflare container IP)
        # Home Assistant's HTTP component populates the forwarders if configured correctly.
        remote_ip = ipaddress.ip_address(request.remote)

        # 2. Define your local network ranges
        is_local = remote_ip.is_private or remote_ip.is_loopback

        # 3. Block if not local
        if not is_local:
            return web.json_response(
                {"error": "Unauthorized: Local network access only"}, status=403
            )

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
