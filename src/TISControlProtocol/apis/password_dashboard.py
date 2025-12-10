from homeassistant.components.http import HomeAssistantView
from aiohttp import web
import logging
import os

_LOGGER = logging.getLogger(__name__)


class PasswordDashboardEndpoint(HomeAssistantView):
    """Custom Dashboard Endpoint with Cookie and Token Auth."""

    url = "/api/password-dashboard"
    name = "api:password-dashboard"
    requires_auth = False

    def __init__(self, views_path):
        self.views_path = views_path

    async def get(self, request):
        file_path = os.path.join(self.views_path, "password_dashboard", "index.html")
        if not os.path.exists(file_path):
            return web.Response(text="Error: Dashboard file not found", status=404)

        return web.FileResponse(file_path)
