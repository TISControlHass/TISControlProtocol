from abc import ABC, abstractmethod
from typing import Optional
from homeassistant.core import HomeAssistant


class BaseService(ABC):
    """Abstract base class for all TIS Control Protocol services."""

    def __init__(self, hass: HomeAssistant, domain: str, name: str) -> None:
        self.hass = hass
        self.domain = domain
        self.name = name
        self.is_running = False

    @abstractmethod
    def start(self) -> None:
        """Start or enable the service."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop or disable the service."""
        pass
