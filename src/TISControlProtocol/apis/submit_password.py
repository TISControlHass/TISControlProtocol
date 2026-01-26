from homeassistant.components.http import HomeAssistantView
from aiohttp import web
import logging
import time


class SubmitPasswordEndpoint(HomeAssistantView):
    """TIS API endpoint."""

    url = "/api/submit-password"
    name = "api:submit-password"
    requires_auth = False

    def __init__(self, tis_api):
        self.tis_api = tis_api

        # Dictionary to store {ip: last_request_time}
        self.rate_limit_data = {}
        self.cooldown_seconds = 5

    async def post(self, request):
        # Get requester IP
        client_ip = request.remote

        logging.warning(f"Received password submission from IP: client_ip {client_ip}")
        logging.warning(f"rate_limit_data: {self.rate_limit_data}")

        # Check Throttle
        current_time = time.time()
        last_request = self.rate_limit_data.get(client_ip, 0)

        if current_time - last_request < self.cooldown_seconds:
            logging.warning(f"Rate limit exceeded for IP: {client_ip}")
            return web.json_response(
                {"error": "Too many requests. Please wait."},
                status=429,  # HTTP 429 Too Many Requests
            )

        # Update the last request time
        self.rate_limit_data[client_ip] = current_time

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
