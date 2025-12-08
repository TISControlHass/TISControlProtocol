from homeassistant.components.http import HomeAssistantView
from aiohttp import web
import logging


class SubmitPasswordEndpoint(HomeAssistantView):
    """TIS API endpoint."""

    url = "/api/submit-password"
    name = "api:submit-password"
    requires_auth = False

    def __init__(self, tis_api):
        self.tis_api = tis_api

    async def post(self, request):
        try:
            data = await request.json()

            if not data or "password" not in data:
                logging.error("Required parameters are missing in the request")
                return web.json_response(
                    {"error": "Required parameters are missing"}, status=400
                )

            password = data["password"]
            event_data = {
                "password": password,
                "feedback_type": "password_feedback",
            }

            self.tis_api.hass.bus.async_fire("password_feedback", event_data)
            logging.warning("password event got fired successfully")

            # Return the response immediately
            return web.json_response({"message": "Password submitted successfully"})
        except Exception as e:
            logging.error(f"Error submitting password: {e}")
            return web.json_response(
                {"error": "Failed to submit the password"}, status=500
            )
