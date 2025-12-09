from homeassistant.components.http import HomeAssistantView
import os
from aiohttp import web


class PasswordDashboardEndpoint(HomeAssistantView):
    """TIS API endpoint."""

    url = "/api/password-dashboard"
    name = "api:password-dashboard"
    requires_auth = True

    def __init__(self, views_path):
        self.views_path = views_path

    async def get(self, request):
        file_path = os.path.join(self.views_path, "password_dashboard", "index.html")
        return web.FileResponse(file_path)
