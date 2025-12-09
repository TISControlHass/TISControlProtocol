from homeassistant.components.http import HomeAssistantView
from aiohttp import web
import logging
import os


class PasswordDashboardEndpoint(HomeAssistantView):
    """Custom Dashboard Endpoint with Cookie Auth."""

    url = "/api/password-dashboard"
    name = "api:password-dashboard"
    requires_auth = False

    def __init__(self, views_path, hass):
        self.hass = hass
        self.views_path = views_path

    async def get(self, request):
        logging.warning(f"request: {request}")
        try:
            hass = request.app["hass"]
            logging.warning("nothing happened")
        except Exception as e:
            logging.error(f"some error happened here! error: {e}")
            hass = self.hass

        user = request.get("hass_user")

        if not user:
            # Get the session cookie sent by the browser
            session_id = request.cookies.get("auth_session_id")
            logging.warning("request cookies")
            logging.warning(request.cookies)
            logging.warning(f"session id: {session_id}")

            if session_id:
                # Ask HA Auth system to find the session
                session = await hass.auth.async_get_session(session_id)
                logging.warning(f"session: {session}")

                # specific check: Session must exist and be active
                if session and session.is_active:
                    user = session.user

        if user is None:
            logging.warning(
                "Unauthorized access attempt to Password Dashboard. Redirecting to login."
            )
            # Redirect to Home Assistant root to trigger login flow
            return web.HTTPFound(location="/")

        if not user.is_admin:
            return web.Response(text="403: Admins only", status=403)

        logging.warning(f"Serving Password Dashboard to user: {user.name}")

        # 4. Serve the file
        file_path = os.path.join(self.views_path, "password_dashboard", "index.html")
        return web.FileResponse(file_path)
