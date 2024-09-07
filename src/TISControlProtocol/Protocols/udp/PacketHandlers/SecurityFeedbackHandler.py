from homeassistant.core import HomeAssistant
import logging


async def handle_security_feedback(hass: HomeAssistant, info: dict):
    """
    Handle the feedback from a security sensor.
    """
    device_id = info["device_id"]
    event_data = {
        "device_id": device_id,
        "feedback_type": "security_feedback",
        "additional_bytes": info["additional_bytes"],
    }
    try:
        hass.bus.async_fire(str(info["device_id"]), event_data)
        logging.error(
            f"control response event fired for {info['device_id']}, additional bytes: {info['additional_bytes']}"
        )
    except Exception as e:
        logging.error(f"error in firing even for feedbackt security: {e}")
