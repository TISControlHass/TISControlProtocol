from homeassistant.components.http import HomeAssistantView
from aiohttp import web
import logging


class GetBillConfigEndpoint(HomeAssistantView):
    """Get Bill Configurations"""

    url = "/api/get-bill-config"
    name = "api:get-bill-config"
    requires_auth = False

    def __init__(self, tis_api):
        self.tis_api = tis_api

    async def post(self, request):
        try:
            if self.tis_api.bill_configs:
                configs = self.tis_api.bill_configs
            else:
                configs = await self.tis_api.get_bill_configs()

            logging.info(f"bill configs: {configs}")

            return web.json_response({"config": configs})
        except Exception as e:
            logging.error(f"Error getting bill config: {e}")
            return web.json_response({"error": "Failed to get bill config"}, status=500)
