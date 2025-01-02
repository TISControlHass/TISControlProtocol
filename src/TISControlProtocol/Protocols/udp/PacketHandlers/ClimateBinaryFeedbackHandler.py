from homeassistant.core import HomeAssistant
import logging

AC_NUMBER_MAP = {0x19: 0, 0x1A: 1, 0x1B: 2, 0x1C: 3, 0x1D: 4, 0x1E: 5, 0x1F: 6, 0x20: 7}
FLOOR_NUMBER_MAP = {0x22: 0, 0x23: 1}

async def handle_climate_binary_feedback(hass: HomeAssistant, info: dict):
    
    
    #check sub_operation or number
    if info["additional_bytes"][0] <= 0x18:
        sub_operation = info["additional_bytes"][0]
        operation_value = info["additional_bytes"][1]

        if info["additional_bytes"][0] < 0x14:
            
            feedback_type = "ac_feedback"
            number = 0
            
        else:
            feedback_type = "floor_feedback"
            number = 0
                

    else:
        ac_number = AC_NUMBER_MAP.get(info["additional_bytes"][0], None)
        floor_number = AC_NUMBER_MAP.get(info["additional_bytes"][0], None)
        sub_operation = info["additional_bytes"][1]
        operation_value = info["additional_bytes"][2]

        if ac_number is not None:
            feedback_type = "ac_feedback"
            number = ac_number

        else:
            feedback_type = "floor_feedback"
            number = floor_number        
        
    event_data = {
    "device_id": info["device_id"],
    "feedback_type": feedback_type,
    "number": number,
    "sub_operation": sub_operation,
    "operation_value": operation_value,
    }
            

    try:
        hass.bus.async_fire(str(info["device_id"]), event_data)
    
    except Exception as e:
        logging.error(f"error in firing event: {e}")
