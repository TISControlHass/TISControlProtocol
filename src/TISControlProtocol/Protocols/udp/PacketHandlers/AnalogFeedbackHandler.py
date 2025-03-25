from homeassistant.core import HomeAssistant
import logging

#TODO get a way to set 4 sensors together
async def handle_analog_feedback(hass: HomeAssistant, info: dict):
    """
    Handle the feedback from an analog sensor.
    """
    device_id = info["device_id"]
    channels_num = int(info["additional_bytes"][0])
    analog = info["additional_bytes"][1:channels_num + 1]

    event_data = {
        "device_id": device_id,
        "feedback_type": "analog_feedback",
        "analog": analog,
        "additional_bytes": info["additional_bytes"],
    }

    try:
        hass.bus.async_fire(str(info["device_id"]), event_data)
    except Exception as e:
        logging.error(f"error in firing event for feedback: {e}")
