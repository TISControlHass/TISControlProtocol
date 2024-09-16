from homeassistant.core import HomeAssistant
import logging

AC_NUMBER_MAP = {0x19: 0, 0x1A: 1, 0x1B: 2, 0x1C: 3, 0x1D: 4, 0x1E: 5, 0x1F: 6, 0x20: 7}


async def handle_climate_binary_feedback(hass: HomeAssistant, info: dict):
    ac_number = AC_NUMBER_MAP.get(info["additional_bytes"][0], None)
    if ac_number is None:
        ac_number = 0
        sub_operation = info["additional_bytes"][0]
        operation_value = info["additional_bytes"][1]

    else:
        sub_operation = info["additional_bytes"][1]
        operation_value = info["additional_bytes"][2]

    event_data = {
        "device_id": info["device_id"],
        "feedback_type": "ac_feedback",
        "ac_number": ac_number,
        "sub_operation": sub_operation,
        "operation_value": operation_value,
    }
    try:
        hass.bus.async_fire(str(info["device_id"]), event_data)
        logging.error(
            f"ac binary feedback event: {event_data} , additional bytes: {info['additional_bytes']}"
        )
    except Exception as e:
        logging.error(f"error in firing event: {e}")
