from homeassistant.components.http import HomeAssistantView
from aiohttp import web
import logging
import os

_LOGGER = logging.getLogger(__name__)


class PasswordDashboardEndpoint(HomeAssistantView):
    """Custom Dashboard Endpoint with Cookie and Token Auth."""

    url = "/api/password-dashboard"
    name = "api:password-dashboard"
    requires_auth = False  # We handle auth manually

    def __init__(self, views_path, hass):
        self.views_path = views_path
        # Store hass reference correctly during init
        self.hass = hass

    async def get(self, request):
        user = None

        if request.get("hass_user"):
            user = request["hass_user"]
            _LOGGER.warning(f"Auth successful via Middleware: {user.name}")

        if not user:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token_str = auth_header.split(" ")[1]
                # Validate the Long-Lived Access Token
                refresh_token = self.hass.auth.async_validate_access_token(token_str)
                if refresh_token:
                    user = refresh_token.user
                    _LOGGER.warning(f"Auth successful via Manual Header: {user.name}")

        if not user:
            session_id = request.cookies.get("auth_session_id")
            if session_id:
                session = await self.hass.auth.async_get_session(session_id)
                if session and session.is_active:
                    user = session.user
                    _LOGGER.warning(f"Auth successful via Manual Cookie: {user.name}")

        if user is None:
            _LOGGER.warning("Unauthorized access. Redirecting to login.")
            # Use HTTPFound (302) to redirect browsers to the login page
            return web.HTTPFound(location="/")

        if not user.is_admin:
            return web.Response(text="403: Admins only", status=403)

        # Serve the file
        file_path = os.path.join(self.views_path, "password_dashboard", "index.html")
        if not os.path.exists(file_path):
            return web.Response(text="Error: Dashboard file not found", status=404)

        return web.FileResponse(file_path)
