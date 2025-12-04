from homeassistant.components.http import HomeAssistantView
import os
from aiohttp import web


class PasswordFormEndpoint(HomeAssistantView):
    """TIS API endpoint."""

    url = "/api/password-form"
    name = "api:password-form"
    requires_auth = False

    def __init__(self, views_path):
        self.views_path = views_path

    async def get(self, request):
        file_path = os.path.join(self.views_path, "password_form", "index.html")
        return web.FileResponse(file_path)
