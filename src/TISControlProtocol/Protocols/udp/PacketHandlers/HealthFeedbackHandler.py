from homeassistant.core import HomeAssistant
import logging


async def handle_health_feedback(hass: HomeAssistant, info: dict):
    """
    Handle the feedback from a health sensor.
    """

    device_id = info["device_id"]

    # this try to know if this device is 10F or health sensor, for 10F it will make all readings 0 except LUX
    try:
        lux = int((info["additional_bytes"][5] << 8) | (info["additional_bytes"][6]))
        noise = int((info["additional_bytes"][7] << 8) | (info["additional_bytes"][8]))
        eco2 = int((info["additional_bytes"][9] << 8) | (info["additional_bytes"][10]))
        tvoc = int((info["additional_bytes"][11] << 8) | (info["additional_bytes"][12]))
        temp = int(info["additional_bytes"][13])
        humidity = int(info["additional_bytes"][14])
        co = int((info["additional_bytes"][27] << 8) | (info["additional_bytes"][28]))
    except Exception as _:
        tvoc = 0
        noise = 0
        temp = 0
        humidity = 0
        eco2 = 0
        co = 0

    event_data = {
        "device_id": device_id,
        "feedback_type": "health_feedback",
        "lux": lux,
        "noise": noise,
        "eco2": eco2,
        "tvoc": tvoc,
        "co": co,
        "temp": temp,
        "humidity": humidity,
        "additional_bytes": info["additional_bytes"],
    }

    try:
        hass.bus.async_fire(str(info["device_id"]), event_data)
    except Exception as e:
        logging.error(f"error in firing event for feedback health: {e}")
