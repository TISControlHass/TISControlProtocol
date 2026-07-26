import logging
from typing import Dict, Optional
from homeassistant.core import HomeAssistant
from .base import BaseService


class ServiceManager:
    """Manager to register and control background and integration services."""

    def __init__(self, hass: HomeAssistant, domain: str) -> None:
        self.hass = hass
        self.domain = domain
        self._services: Dict[str, BaseService] = {}

    def register(self, service: BaseService) -> None:
        """Register a service with the manager."""
        if service.name in self._services:
            logging.warning(f"Service '{service.name}' is already registered.")
            return
        self._services[service.name] = service
        logging.info(f"Registered service: '{service.name}'")

    def get(self, name: str) -> Optional[BaseService]:
        """Get a registered service by name."""
        return self._services.get(name)

    def start(self, name: str) -> None:
        """Start a specific service."""
        service = self.get(name)
        if service and not service.is_running:
            try:
                service.start()
                logging.info(f"Started service: '{name}'")
            except Exception as e:
                logging.error(f"Error starting service '{name}': {e}")

    def stop(self, name: str) -> None:
        """Stop a specific service."""
        service = self.get(name)
        if service and service.is_running:
            try:
                service.stop()
                logging.info(f"Stopped service: '{name}'")
            except Exception as e:
                logging.error(f"Error stopping service '{name}': {e}")

    def toggle(self, name: str, enable: bool) -> None:
        """Enable or disable a specific service."""
        if enable:
            self.start(name)
        else:
            self.stop(name)

    def stop_all(self) -> None:
        """Stop all running services."""
        for service in self._services.values():
            if service.is_running:
                try:
                    service.stop()
                    logging.info(f"Stopped service: '{service.name}'")
                except Exception as e:
                    logging.error(f"Error stopping service '{service.name}': {e}")
