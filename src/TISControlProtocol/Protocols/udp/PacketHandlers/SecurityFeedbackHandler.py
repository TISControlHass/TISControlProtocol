from homeassistant.core import HomeAssistant
import logging

import asyncio
from TISControlProtocol.shared import ack_events



async def handle_security_feedback(hass: HomeAssistant, info: dict):
    """
    Handle the feedback from a security sensor.
    """
    channel_number = info["additional_bytes"][0]
    mode = info["additional_bytes"][1]
    event_data = {
        "device_id": info["device_id"],
        "feedback_type": "security_feedback",
        "additional_bytes": info["additional_bytes"],
        "channel_number": channel_number,
        "mode": mode,
    }
    try:
        hass.bus.async_fire(str(info["device_id"]), event_data)
        logging.info(
            f"control response event fired for {info['device_id']}, additional bytes: {info['additional_bytes']}"
        )
    except Exception as e:
        logging.error(f"error in firing event for feedback security: {e}")

    try:
        event: asyncio.Event = ack_events.get(
            (
                tuple(info["device_id"]),
                (0x01, 0x04),
                int(channel_number),
            )
        )
        if event is not None:
            event.set()
    except Exception as e:
        logging.error(f"error in setting event for {info["device_id"]}: {e}")
