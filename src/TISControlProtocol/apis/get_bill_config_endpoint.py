import ipaddress
import logging

from aiohttp import web
from homeassistant.components.http import HomeAssistantView


class GetBillConfigEndpoint(HomeAssistantView):
    """Get Bill Configurations"""

    url = "/api/get-bill-config"
    name = "api:get-bill-config"
    requires_auth = False

    def __init__(self, tis_api):
        self.tis_api = tis_api

    async def get(self, request):
        remote_ip = ipaddress.ip_address(request.remote)
        is_local = remote_ip.is_private or remote_ip.is_loopback

        if not is_local:
            return web.json_response(
                {"error": "Unauthorized: Local network access only"}, status=403
            )

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
