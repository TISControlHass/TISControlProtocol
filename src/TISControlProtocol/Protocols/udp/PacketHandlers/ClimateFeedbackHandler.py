from TISControlProtocoll.shared import ack_events
import asyncio
from homeassistant.core import HomeAssistant

import logging


async def handle_climate_feedback(hass: HomeAssistant, info: dict):
    logging.error(f"got ac feedback {info}")
