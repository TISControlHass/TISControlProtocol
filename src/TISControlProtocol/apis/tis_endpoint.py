from homeassistant.components.http import HomeAssistantView
from aiohttp import web
import asyncio


class TISEndPoint(HomeAssistantView):
    """TIS API endpoint."""

    url = "/api/tis"
    name = "api:tis"
    requires_auth = False

    def __init__(self, tis_api):
        """Initialize the API endpoint."""
        self.api = tis_api

    async def post(self, request):
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
