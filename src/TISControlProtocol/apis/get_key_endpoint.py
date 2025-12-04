from homeassistant.components.http import HomeAssistantView
from aiohttp import web
from TISControlProtocol.shared import get_real_mac


class GetKeyEndpoint(HomeAssistantView):
    """Get Key API endpoint."""

    url = "/api/get_key"
    name = "api:get_key"
    requires_auth = False

    def __init__(self, tis_api):
        """Initialize the API endpoint."""
        self.api = tis_api

    async def get(self, request):
        # Get the MAC address
        mac_address = await get_real_mac("end0")
        if mac_address is None:
            return web.json_response(
                {"error": "Could not retrieve MAC address"}, status=500
            )

        # Return the MAC address
        return web.json_response({"key": mac_address})
