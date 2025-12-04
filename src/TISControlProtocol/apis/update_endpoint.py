from homeassistant.components.http import HomeAssistantView
from aiohttp import web
import asyncio
from TISControlProtocol.shared import get_real_mac
import logging


class UpdateEndpoint(HomeAssistantView):
    """Update the Server"""

    url = "/api/update"
    name = "api:update"
    requires_auth = False

    def __init__(self, tis_api):
        self.tis_api = tis_api

    async def post(self, request):
        mac_address = request.query.get("mac_address")

        if mac_address is None:
            logging.info("Required parameters not found in query, parsing request body")
            data = await request.json()
            mac_address = data.get("mac_address")

        mac = await get_real_mac("end0")

        if mac_address is None:
            return web.json_response(
                {"error": "required parameters are missing"}, status=400
            )
        elif mac_address != mac:
            return web.json_response({"error": "Unauthorized"}, status=403)

        try:
            integration_dir = self.tis_api.hass.config.path(
                "custom_components", "tis_integration"
            )

            async def run(cmd, cwd):
                """Run a shell command in cwd, return (exit_code, stdout, stderr)."""
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    cwd=cwd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                out, err = await proc.communicate()
                return proc.returncode, out.decode().strip(), err.decode().strip()

            results = {}
            name, path = ("integration", integration_dir)
            code, out, err = await run(["git", "reset", "--hard", "HEAD"], cwd=path)
            results[f"{name}_reset"] = {"code": code, "stdout": out, "stderr": err}
            if code != 0:
                logging.error("Reset %s failed: %s", name, err)
                return web.json_response(
                    {
                        "error": f"{name} reset failed",
                        "details": results[name + "_reset"],
                    },
                    status=500,
                )

            code, out, err = await run(["git", "pull"], cwd=path)
            results[f"{name}_pull"] = {"code": code, "stdout": out, "stderr": err}
            if code != 0:
                logging.error("Pull %s failed: %s", name, err)
                return web.json_response(
                    {
                        "error": f"{name} pull failed",
                        "details": results[name + "_pull"],
                    },
                    status=500,
                )

            logging.info("Successfully updated integration")
            return web.json_response(
                {
                    "message": "TIS integrations updated successfully",
                    "results": results,
                }
            )

        except Exception as e:
            logging.error(f"Could Not Update Server: {e}")
            return web.json_response({"error": "Failed to update server"}, status=500)
