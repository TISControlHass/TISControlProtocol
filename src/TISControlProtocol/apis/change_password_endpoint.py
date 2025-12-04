from homeassistant.components.http import HomeAssistantView
from aiohttp import web
import asyncio
import logging


class ChangeSecurityPassEndpoint(HomeAssistantView):
    """Change Security Password API Endpoint."""

    url = "/api/change_pass"
    name = "api:change_pass"
    requires_auth = False

    def __init__(self, tis_api):
        self.tis_api = tis_api

    async def post(self, request):
        try:
            old_pass = request.query.get("old_pass")
            new_pass = request.query.get("new_pass")
            confirm_pass = request.query.get("confirm_pass")

            if old_pass is None or new_pass is None or confirm_pass is None:
                logging.info(
                    "Required parameters not found in query, parsing request body"
                )
                data = await request.json()
                old_pass = old_pass or data.get("old_pass")
                new_pass = new_pass or data.get("new_pass")
                confirm_pass = confirm_pass or data.get("confirm_pass")

            if old_pass is None or new_pass is None or confirm_pass is None:
                logging.error("Missing required parameters")
                return web.json_response(
                    {
                        "message": "error",
                        "error": "Missing required parameters",
                    },
                    status=400,
                )

        except Exception as e:
            logging.error(f"Error parsing request: {e}")
            return web.json_response(
                {"message": "error", "error": "Invalid request parameters"},
                status=400,
            )

        if old_pass != self.tis_api.config_entries["lock_module"]["password"]:
            return web.json_response(
                {
                    "message": "error",
                    "error": "Old password is incorrect, please try again",
                },
                status=403,
            )

        if new_pass == old_pass:
            return web.json_response(
                {
                    "message": "error",
                    "error": "New password must be different from the old password",
                },
                status=400,
            )

        if len(new_pass) < 4:
            return web.json_response(
                {
                    "message": "error",
                    "error": "Password must be at least 4 characters long",
                },
                status=400,
            )

        if new_pass != confirm_pass:
            return web.json_response(
                {
                    "message": "error",
                    "error": "New password and confirmation do not match",
                },
                status=400,
            )

        directory = "/config/custom_components/tis_integration/"
        data = await self.tis_api.read_appliances(directory=directory)
        data["configs"]["lock_module_password"] = new_pass
        await self.tis_api.save_appliances(data, directory)
        self.tis_api.config_entries["lock_module"]["password"] = new_pass

        asyncio.create_task(self.reload_platforms())

        return web.json_response(
            {
                "message": "success",
            }
        )

    async def reload_platforms(self):
        for entry in self.tis_api.hass.config_entries.async_entries(
            self.tis_api.domain
        ):
            await self.tis_api.hass.config_entries.async_reload(entry.entry_id)
