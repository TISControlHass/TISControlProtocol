from homeassistant.components.http import HomeAssistantView
import os
from aiohttp import web
import logging


class PasswordFormEndpoint(HomeAssistantView):
    """TIS API endpoint."""

    url = "/api/password-form"
    name = "api:password-form"
    requires_auth = False

    def __init__(self, views_path):
        self.views_path = views_path

    async def get(self, request):
        file_path = os.path.join(self.views_path, "password_form", "index.html")
        try:
            return web.FileResponse(file_path)
        except Exception as e:
            logging.error(f"Error occurred while serving password form: {e}")
            return web.json_response(
                {"error": "Failed to serve password form"}, status=500
            )
