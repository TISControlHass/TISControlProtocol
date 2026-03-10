from TISControlProtocol.shared import ack_events
import asyncio
from homeassistant.core import HomeAssistant

import logging


async def handle_climate_control_feedback(hass: HomeAssistant, info: dict):
    additional_bytes = info["additional_bytes"]

    # Luna sends F8 (for success or F5 for fail) at the beginning of the
    # additional_bytes unlike the 10 function that doesn't send that F8
    if additional_bytes[0] == 0xF8:  # Luna case!
        ac_number = additional_bytes[1]
        state = additional_bytes[2]
        cool_temp = additional_bytes[3]
        hvac_mode = (additional_bytes[4] >> 4) & 0x0F
        fan_speed = additional_bytes[4] & 0x0F
        heat_temp = additional_bytes[7]
        auto_temp = additional_bytes[9]

    else:  # Most probably the 10 function
        state = additional_bytes[0]
        cool_temp = additional_bytes[1]
        hvac_mode = (additional_bytes[2] >> 4) & 0x0F
        fan_speed = additional_bytes[2] & 0x0F
        heat_temp = additional_bytes[5]
        auto_temp = additional_bytes[7]
        ac_number = 0

    event_data = {
        "device_id": info["device_id"],
        "feedback_type": "update_feedback",
        "ac_number": ac_number,
        "state": state,
        "cool_temp": cool_temp,
        "hvac_mode": hvac_mode,
        "fan_speed": fan_speed,
        "heat_temp": heat_temp,
        "auto_temp": auto_temp,
    }

    try:
        hass.bus.async_fire(str(info["device_id"]), event_data)
    except Exception as e:
        logging.error(f"error in firing event for feedback: {e}")

    try:
        event: asyncio.Event | None = ack_events.get(
            (
                tuple(info["device_id"]),
                (0xE0, 0xEE),
                ac_number,
            )
        )
        if event is not None:
            logging.info(
                f"setting event for climate control feedback, {info['device_id']}"
            )
            event.set()
    except Exception as e:
        logging.error(f"error in setting event for feedback: {e}")
