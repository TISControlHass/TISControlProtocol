from homeassistant.core import HomeAssistant  # type: ignore
import logging
import asyncio
from TISControlProtocol.shared import ack_events


async def handle_security_update_feedback (hass: HomeAssistant, info: dict):
    # remove auxilary bytes which represents number of scenarios
    channel_number = info["additional_bytes"][0]
    mode = info["additional_bytes"][1]
    event_data = {
        "device_id": info["device_id"],
        "feedback_type": "security_update",
        "additional_bytes": info["additional_bytes"],
        "channel_number": channel_number,
        "mode": mode,
    }
    try:
        hass.bus.async_fire(str(info["device_id"]), event_data)
    except Exception as e:
        logging.error(f"error in firing event: {e}")

    try:
        event: asyncio.Event = ack_events.get(
            (
                tuple(info["device_id"]),
                (0x01, 0x1E),
                int(channel_number),
            )
        )
        if event is not None:
            event.set()
    except Exception as e:
        logging.error(f'error in setting event for: {info["device_id"]}, {e}')