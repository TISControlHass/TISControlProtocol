from homeassistant.core import HomeAssistant
import logging


async def handle_health_feedback(hass: HomeAssistant, info: dict):
    """
    Handle the feedback from a health sensor.
    """
    device_id = info["device_id"]
    lux = int((info["additional_bytes"][5]<<8)|(info["additional_bytes"][6]))
    temp = int(info["additional_bytes"][15])
    event_data = {
        "device_id": device_id,
        "feedback_type": "health_feedback",
        "lux": lux,
        "temp": temp,
        "additional_bytes": info["additional_bytes"],
    }
    
    try:
        hass.bus.async_fire(str(info["device_id"]), event_data)
        # logging.error(
        #     f"control response event fired for {info['device_id']}, additional bytes: {info['additional_bytes']}"
        # )
    except Exception as e:
        logging.error(f"error in firing even for feedbackt health: {e}")
