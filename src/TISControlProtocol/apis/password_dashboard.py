from homeassistant.components.http import HomeAssistantView
import os
from aiohttp import web
import logging


class PasswordDashboardEndpoint(HomeAssistantView):
    """TIS API endpoint."""

    url = "/password-dashboard"
    name = "password-dashboard"
    requires_auth = False

    def __init__(self, views_path):
        self.views_path = views_path

    async def get(self, request):
        logging.warning("checking authenticity")
        logging.warning(f"request: {request}")
        if request.get("hass_user") is None:
            logging.warning("not authenticated...")
            logging.warning("routing to the home page")
            # If no user is found, redirect them to the main HA interface (which forces login)
            return web.HTTPFound(location="/")

        file_path = os.path.join(self.views_path, "password_dashboard", "index.html")
        return web.FileResponse(file_path)
