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
    dry_temp = info["additional_bytes"][10]

    event_data = {
        "device_id": info["device_id"],
        "ac_number": ac_number,
        "state": state,
        "cool_temp": cool_temp,
        "hvac_mode": hvac_mode,
        "fan_speed": fan_speed,
        "heat_temp": heat_temp,
        "auto_temp": auto_temp,
        "dry_temp": dry_temp,
    }
    logging.info(f"climate control feedback: {event_data}")

    try:
        hass.bus.async_fire(str(info["device_id"]), event_data)
    except Exception as e:
        logging.error(f"error in firing even for feedbackt: {e}")

    try:
        event: asyncio.Event = ack_events.get(
            (
                tuple(info["device_id"]),
                (0xE0, 0xEE),
                ac_number,
            )
        )
        if event is not None:
            print("setting event")
            event.set()
    except Exception as e:
        print(e)
