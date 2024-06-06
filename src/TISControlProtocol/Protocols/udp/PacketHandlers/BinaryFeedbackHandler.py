from homeassistant.core import HomeAssistant  # type: ignore
import logging


async def handle_binary_feedback(hass: HomeAssistant, info: dict):
    # remove auxilary bytes which represents number of scenarios
    len_aux = info["additional_bytes"][0]
    info["additional_bytes"] = info["additional_bytes"][len_aux + 1 :]
    event_data = {
        "device_id": info["device_id"],
        "feedback_type": "binary_feedback",
        "additional_bytes": info["additional_bytes"],
    }
    try:
        hass.bus.async_fire(str(info["device_id"]), event_data)
    except Exception as e:
        logging.error(f"error in firing event: {e}")
