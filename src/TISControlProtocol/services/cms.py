import logging
from datetime import timedelta
from typing import Optional

import aiohttp
import psutil
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval

from TISControlProtocol.shared import get_real_mac
from .base import BaseService


class CMSDataSender:
    """CMS Data Sender class for posting system health data."""

    def __init__(self, external_url: str, hass: HomeAssistant) -> None:
        self.external_url = external_url
        self.hass = hass

    async def send_data(self, data: dict) -> bool:
        if data is not None:
            try:
                session = async_get_clientsession(self.hass)
                async with session.post(self.external_url, json=data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logging.warning(f"Error sending data to CMS: {response.status}")
                        logging.info(f"Error response: {error_text}")
                        return False
                    else:
                        logging.info("Data sent to CMS successfully")
                        return True
            except aiohttp.ClientError as e:
                logging.warning(f"ClientError while sending data to CMS: {e}")
                return False

        return False


class CMSService(BaseService):
    """Service to collect system metrics and deliver data to CMS."""

    def __init__(
        self,
        hass: HomeAssistant,
        domain: str,
        cms_url: str = "https://cms-tis.com",
    ) -> None:
        super().__init__(hass, domain, name="cms")
        self.cms_url = cms_url
        self._cms_task_unsub = None
        self.sender = CMSDataSender(
            external_url=f"{self.cms_url}/api/device-health",
            hass=self.hass,
        )

    def start(self) -> None:
        """Register CMS HA service and schedule periodic collection task."""
        if self.is_running:
            return
        self._register_services()
        self._schedule_cms_data_task()
        self.is_running = True

    def stop(self) -> None:
        """Unregister CMS HA service and cancel periodic task."""
        if not self.is_running:
            return
        self._unregister_cms_services()
        self.is_running = False

    def _register_services(self) -> None:
        """Register Home Assistant services."""
        if self.hass.services.has_service(self.domain, "send_cms_data"):
            return

        logging.info("Registering CMS data service")

        async def handle_cms_data(call):
            data = call.data.get("data", None)

            if data is None:
                logging.error("No data provided to send to CMS")
                return

            await self.sender.send_data(data)

        self.hass.services.async_register(
            self.domain,
            "send_cms_data",
            handle_cms_data,
        )

    def _schedule_cms_data_task(self) -> None:
        """Schedule periodic CMS data task."""

        async def scheduled_task(now=None):
            try:
                data = await self.collect_system_data()

                await self.hass.services.async_call(
                    self.domain,
                    "send_cms_data",
                    {"data": data},
                )
            except Exception as e:
                logging.error(f"Error getting data for CMS: {e}")

        if self._cms_task_unsub:
            self._cms_task_unsub()

        interval = timedelta(minutes=3)
        self._cms_task_unsub = async_track_time_interval(
            self.hass, scheduled_task, interval
        )

    def _unregister_cms_services(self) -> None:
        """Unregister CMS service and stop periodic task."""
        if self.hass.services.has_service(self.domain, "send_cms_data"):
            self.hass.services.async_remove(self.domain, "send_cms_data")

        logging.info("CMS data service unregistered")

        if self._cms_task_unsub:
            self._cms_task_unsub()
            self._cms_task_unsub = None

    async def collect_system_data(self) -> dict:
        """Collect system data for CMS."""
        # Mac Address
        mac_address = await get_real_mac("end0")

        # CPU Usage
        cpu_usage = await self.hass.async_add_executor_job(psutil.cpu_percent, 1)

        # CPU Temperature
        cpu_temp = await self.hass.async_add_executor_job(psutil.sensors_temperatures)
        cpu_temp = cpu_temp.get("cpu_thermal", None)
        cpu_temp = cpu_temp[0].current if cpu_temp else 0

        # Disk Usage
        total, _, free, percent = await self.hass.async_add_executor_job(
            psutil.disk_usage, "/"
        )

        # Memory Usage
        mem = await self.hass.async_add_executor_job(psutil.virtual_memory)

        return {
            "mac_address": mac_address,
            "cpu_usage": cpu_usage,
            "cpu_temperature": cpu_temp,
            "disk_total": total,
            "disk_free": free,
            "disk_percent": percent,
            "ram_total": mem.total,
            "ram_free": mem.free,
            "ram_percent": mem.percent,
        }
