from homeassistant.core import HomeAssistant

import logging
import asyncio
from TISControlProtocol.shared import ack_events


async def handle_control_response(hass: HomeAssistant, info: dict):
    channel_number = info["additional_bytes"][0]
    event_data = {
        "device_id": info["device_id"],
        "channel_number": channel_number,
        "feedback_type": "control_response",
        "additional_bytes": info["additional_bytes"],
    }
    try:
        hass.bus.async_fire(str(info["device_id"]), event_data)
    except Exception as e:
        logging.error(f"error in firing even for feedbackt: {e}")

    try:
        event: asyncio.Event = ack_events.get(
            (
                tuple(info["device_id"]),
                (0x00, 0x31),
                int(channel_number),
            )
        )
        if event is not None:
            event.set()
    except Exception as e:
        logging.error(f"error getting the acknowledge event e: {e}")
