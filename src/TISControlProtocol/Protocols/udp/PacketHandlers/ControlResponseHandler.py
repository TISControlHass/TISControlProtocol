from homeassistant.core import HomeAssistant

import logging
import asyncio
from TISControlProtocol.shared import ack_events


async def handle_control_response(hass: HomeAssistant, info: dict):
    channel_number = info["additional_bytes"][0]
    # await target_appliance.handle_packet(info["additional_bytes"], "control")
    event_data = {
        "device_id": info["device_id"],
        "channel_number": channel_number,
        "feedback_type": "control_response",
        "additional_bytes": info["additional_bytes"],
    }
    try:
        hass.bus.async_fire(str(info["device_id"]), event_data)
    except Exception as e:
        logging.error(f"error in firing event for feedback: {e}")

    try:
        event: asyncio.Event = ack_events.get(
            (
                tuple(info["device_id"]),
                (0x00, 0x31),
                int(channel_number),
            )
        )
        if event is not None:
            logging.info(f"setting event for control response {info["device_id"]}")
            event.set()
    except Exception as e:
        logging.error(f"error in setting event for feedback: {e}")
