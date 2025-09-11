from homeassistant.core import HomeAssistant

import logging


async def handle_real_time_feedback(hass: HomeAssistant, info: dict):
    channel_number = info["additional_bytes"][0]
    if info["source_device_id"] == [0x64, 0x64]:
        event_data = {
            "device_id": info["device_id"],
            "channel_number": channel_number,
            "feedback_type": "realtime_feedback",
            "additional_bytes": info["additional_bytes"],
        }
        try:
            hass.bus.async_fire(str(info["device_id"]), event_data)
        except Exception as e:
            logging.error(f"error in firing even for feedbackt: {e}")
