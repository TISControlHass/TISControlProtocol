from homeassistant.components.http import HomeAssistantView
from aiohttp import web
import logging


class PasswordsEndpoint(HomeAssistantView):
    """TIS API endpoint."""

    url = "/api/password-dashboard/passwords"
    name = "api:password-dashboard:passwords"

    def __init__(self, tis_api):
        self.tis_api = tis_api

    async def get(self, request: web.Request):
        try:
            passwords = await self.tis_api.get_passwords()
            logging.info("passwords got successfully!")
            return web.json_response(passwords)
        except Exception as e:
            logging.error(
                f"Something went wrong while saving password entities, error: {e}"
            )
            return web.json_response({"error": "Failed to save passwords"}, status=500)

    async def post(self, request: web.Request):
        data = await request.json()

        if not data:
            logging.error("Required parameters are missing in the request")
            return web.json_response(
                {"error": "Required parameters are missing"}, status=400
            )

        try:
            await self.tis_api.save_passwords(data)
            logging.info("passwords saved successfully!")
            return web.json_response({"message": "Passwords saved successfully"})
        except Exception as e:
            logging.error(
                f"Something went wrong while saving password entities, error: {e}"
            )
            return web.json_response({"error": "Failed to save passwords"}, status=500)
