from homeassistant.components.http import HomeAssistantView
from aiohttp import web
import asyncio
import logging
import os
import json
import aiofiles


class BillConfigEndpoint(HomeAssistantView):
    """Save Bill Configurations"""

    url = "/api/bill-config"
    name = "api:bill-config"
    requires_auth = False

    def __init__(self, tis_api):
        self.tis_api = tis_api

    async def post(self, request):
        try:
            data = await request.json()

            if not data or "summer_rates" not in data or "winter_rates" not in data:
                logging.error("Required parameters are missing in the request")
                return web.json_response(
                    {"error": "Required parameters are missing"}, status=400
                )

            directory = "/config/custom_components/tis_integration/"
            os.makedirs(directory, exist_ok=True)

            file_name = "bill.json"
            output_file = os.path.join(directory, file_name)

            async with aiofiles.open(output_file, "w") as f:
                await f.write(json.dumps(data, indent=4))

            self.tis_api.bill_configs = data

            # Start reload operations in the background
            asyncio.create_task(self.reload_platforms())

            # Return the response immediately
            return web.json_response({"message": "Bill config saved successfully"})
        except Exception as e:
            logging.error(f"Error saving bill config: {e}")
            return web.json_response(
                {"error": "Failed to save bill config"}, status=500
            )

    async def reload_platforms(self):
        # Reload the platforms
        for entry in self.api.hass.config_entries.async_entries(self.api.domain):
            await self.api.hass.config_entries.async_reload(entry.entry_id)
