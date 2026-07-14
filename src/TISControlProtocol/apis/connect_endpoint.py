from homeassistant.components.http import HomeAssistantView
from aiohttp import web
from TISControlProtocol.shared import get_real_mac
import logging


class ToggleConnectionEndpoint(HomeAssistantView):
    """Connect or Disconnect the TIS API"""

    url = "/api/toggle-connection"
    name = "api:toggle-connection"
    requires_auth = False

    def __init__(self, tis_api):
        self.tis_api = tis_api

    async def post(self, request):
        mac_address = request.query.get("mac_address")

        if mac_address is None:
            logging.info("Required parameters not found in query, parsing request body")
            try:
                data = await request.json()
                mac_address = data.get("mac_address")
            except Exception:
                pass

        mac = await get_real_mac("end0")

        if mac_address is None:
            return web.json_response(
                {"error": "required parameters are missing"}, status=400
            )
        elif mac_address != mac:
            return web.json_response({"error": "Unauthorized"}, status=403)

        if self.tis_api.transport:
            logging.info("Disconnecting from TIS API")
            try:
                await self.tis_api.disconnect()
                return web.json_response({"message": "Disconnected"}, status=200)
            except Exception as e:
                logging.error(f"Error disconnecting: {e}")
                return web.json_response({"error": "Failed to disconnect"}, status=500)
        else:
            logging.info("Connecting to TIS API")
            try:
                await self.tis_api.connect()
                return web.json_response({"message": "Connected"}, status=200)
            except Exception as e:
                logging.error(f"Error connecting: {e}")
                return web.json_response({"error": "Failed to connect"}, status=500)
