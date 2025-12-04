from homeassistant.components.http import HomeAssistantView
from aiohttp import web
from TISControlProtocol.shared import get_real_mac
import logging


class RestartEndpoint(HomeAssistantView):
    """Restart the Server"""

    url = "/api/restart"
    name = "api:restart"
    requires_auth = False

    def __init__(self, tis_api):
        self.tis_api = tis_api

    async def post(self, request):
        mac_address = request.query.get("mac_address")

        if mac_address is None:
            logging.info("Required parameters not found in query, parsing request body")
            data = await request.json()
            mac_address = data.get("mac_address")

        mac = await get_real_mac("end0")

        if mac_address is None:
            return web.json_response(
                {"error": "required parameters are missing"}, status=400
            )
        elif mac_address != mac:
            return web.json_response({"error": "Unauthorized"}, status=403)

        logging.info("Restarting Server")
        try:
            await self.tis_api.hass.services.async_call(
                "homeassistant", "restart", {}, blocking=False
            )
            return web.json_response({"message": "Server is restarting"}, status=200)
        except Exception as e:
            logging.error(f"Error restarting server: {e}")
            return web.json_response({"error": "Failed to restart server"}, status=500)
