from TISControlProtocol.shared import ack_events
import asyncio
from homeassistant.core import HomeAssistant

import logging


async def handle_climate_control_feedback(hass: HomeAssistant, info: dict):
    ac_number = info["additional_bytes"][1]
    state = info["additional_bytes"][2]
    cool_temp = info["additional_bytes"][3]
    hvac_mode = (info["additional_bytes"][4] >> 4) & 0x0F
    fan_speed = info["additional_bytes"][4] & 0x0F
    heat_temp = info["additional_bytes"][7]
    auto_temp = info["additional_bytes"][9]

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
