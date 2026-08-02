import asyncio
import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval

from TISControlProtocol.Protocols.udp.ProtocolHandler import (
    TISProtocolHandler,
)
from TISControlProtocol.shared import get_real_mac

from .base import BaseService
from .cms import CMSDataSender

protocol_handler = TISProtocolHandler()


class TISDevice:
    def __init__(self, tis_api, device) -> None:
        self.api = tis_api
        addr = device["device_address"]
        if isinstance(addr, str):
            self.device_id = [int(x.strip()) for x in addr.split(",") if x.strip()]
        else:
            self.device_id = [int(x) for x in addr]
        self.device_type_code = device["device_type_code"]
        self.device_type_name = device["device_name"]
        self.gateway = str(device["gateway"])


class DeviceScanService(BaseService):
    """Service to periodically scan TIS network devices and report to CMS."""

    def __init__(
        self,
        hass: HomeAssistant,
        domain: str,
        tis_api,
        cms_url: str = "https://cms-tis.com",
    ) -> None:
        super().__init__(hass, domain, name="scan_devices")
        self.api = tis_api
        self.cms_url = cms_url
        self._scan_task_unsub = None
        self.sender = CMSDataSender(
            external_url=f"{self.cms_url}/api/scan-devices",
            hass=self.hass,
        )

    def start(self) -> None:
        """Start periodic device scanning."""
        if self.is_running:
            return
        self._register_services()
        self._schedule_scan_task()
        self.is_running = True

    def stop(self) -> None:
        """Stop periodic device scanning."""
        if not self.is_running:
            return
        self._unregister_services()
        self.is_running = False

    def _register_services(self) -> None:
        """Register Home Assistant services."""
        if self.hass.services.has_service(self.domain, "scan_devices"):
            return

        logging.info("Registering Device Scan service")

        async def handle_scan_devices(call):
            await self.scan_and_send()

        self.hass.services.async_register(
            self.domain,
            "scan_devices",
            handle_scan_devices,
        )

    def _unregister_services(self) -> None:
        """Unregister Device Scan service and stop periodic task."""
        if self.hass.services.has_service(self.domain, "scan_devices"):
            self.hass.services.async_remove(self.domain, "scan_devices")

        logging.info("Device Scan service unregistered")

        if self._scan_task_unsub:
            self._scan_task_unsub()
            self._scan_task_unsub = None

    def _schedule_scan_task(self) -> None:
        """Schedule 30-minute device scanning task."""

        async def scheduled_task(now=None):
            try:
                await self.scan_and_send()
            except Exception as e:
                logging.error(f"Error during scheduled device scan: {e}")

        if self._scan_task_unsub:
            self._scan_task_unsub()

        interval = timedelta(minutes=30)
        self._scan_task_unsub = async_track_time_interval(
            self.hass, scheduled_task, interval
        )

    async def scan_and_send(self) -> bool:
        """Perform network device scan and send payload to CMS."""
        logging.info("Starting periodic device scan for CMS")
        connected_devices = await self.discover_network_devices()
        devices = [
            {
                "device_id": device["device_id"],
                "device_type_code": device["device_type"],
                "device_type_name": self.api.devices_dict.get(
                    tuple(device["device_type"]), tuple(device["device_type"])
                ),
                "gateway": device["source_ip"],
            }
            for device in connected_devices
        ]

        mac_address = await get_real_mac("end0")
        payload = {
            "mac_address": mac_address,
            "devices": devices,
        }

        return await self.sender.send_data(payload)

    async def discover_network_devices(self, attempts=5) -> list:
        """Discover network devices by broadcasting discovery packets."""
        self.api.hass.data[self.api.domain]["discovered_devices"] = []

        for device_dict in self.api.raw_devices:
            device = TISDevice(self.api, device_dict)
            packet = protocol_handler.generate_heartbeat_packet(device)
            await self.api.protocol.sender.send_packet_with_ack(
                packet, attempts=attempts
            )
        return self.api.hass.data[self.api.domain]["discovered_devices"]
