from homeassistant.core import HomeAssistant  # type: ignore
import logging


async def handle_auto_binary_feedback(hass: HomeAssistant, info: dict):
    logging.info(f"Auto Binary Feedback: {info}")
    channels_number: int = info["additional_bytes"][0]
    channels_values: list = info["additional_bytes"][channels_number :]

    event_data = {
        "device_id": info["device_id"],
        "feedback_type": "auto_binary_feedback",
        "channels_values": channels_values,
    }
    # try:
    #     hass.bus.async_fire(str(info["device_id"]), event_data)
    # except Exception as e:
    #     logging.error(f"error in firing event: {e}")
