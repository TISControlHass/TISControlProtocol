from homeassistant.core import HomeAssistant
import logging


async def handle_luna_temp_feedback(hass: HomeAssistant, info: dict):
    """
    Handle the feedback from a Luna temperature sensor.
    """
    device_id = info["device_id"]
    temperature = int(info["additional_bytes"][1])

    event_data = {
        "device_id": device_id,
        "feedback_type": "temp_feedback",
        "temp": temperature,
        "additional_bytes": info["additional_bytes"],
    }

    try:
        hass.bus.async_fire(str(info["device_id"]), event_data)
    except Exception as e:
        logging.error(f"error in firing event for feedback: {e}")
