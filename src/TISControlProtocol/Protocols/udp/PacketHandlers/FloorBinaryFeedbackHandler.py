from homeassistant.core import HomeAssistant
import logging


async def handle_floor_binary_feedback(hass: HomeAssistant, info: dict):
    # check sub_operation or number
    number = info["additional_bytes"][0]
    state = info["additional_bytes"][3]
    temp = info["additional_bytes"][5]

    event_data = {
        "device_id": info["device_id"],
        "feedback_type": "floor_update",
        "heater_number": number,
        "state": state,
        "temp": temp,
    }

    try:
        hass.bus.async_fire(str(info["device_id"]), event_data)

    except Exception as e:
        logging.error(f"error in firing event: {e}")
