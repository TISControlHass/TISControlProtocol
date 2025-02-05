from homeassistant.core import HomeAssistant
import logging
import struct

wind_direction_dict = {0x01:"north", 0x02:"north east", 0x04:"east", 0x08:"south east", 0x10:"south", 0x20:"south west", 0x40:"west", 0x80:"north west", }
def big_endian_to_float( value ):
    binary = value.to_bytes(4, 'big')
    float_value = struct.unpack('.>f', binary)
    return float_value

async def handle_weather_feedback(hass: HomeAssistant, info: dict):
    """
    Handle the feedback from a health sensor.
    """
    device_id = info["device_id"]
    wind_direction = wind_direction_dict[int(info["additional_bytes"][3])]
    temperature = big_endian_to_float(int((info["additional_bytes"][4]<<24)|(info["additional_bytes"][5]<<16)|(info["additional_bytes"][6]<<8)|info["additional_bytes"][7]))
    humidity = int(info["additional_bytes"][8])
    wind_speed = big_endian_to_float(int((info["additional_bytes"][9]<<24)|(info["additional_bytes"][10]<<16)|(info["additional_bytes"][11]<<8)|info["additional_bytes"][12]))
    gust_speed = big_endian_to_float(int((info["additional_bytes"][13]<<24)|(info["additional_bytes"][14]<<16)|(info["additional_bytes"][15]<<8)|info["additional_bytes"][16]))
    rainfall = int((info["additional_bytes"][17]<<8)|(info["additional_bytes"][18]))
    lighting = big_endian_to_float(int((info["additional_bytes"][19]<<24)|(info["additional_bytes"][20]<<16)|(info["additional_bytes"][21]<<8)|info["additional_bytes"][22]))
    uv = int(info["additional_bytes"][23])



    event_data = {
        "device_id": device_id,
        "feedback_type": "health_feedback",
        "wind": wind_direction,
        "temperature": temperature,
        "humidity": humidity,
        "wind_speed": wind_speed,
        "gust_speed": gust_speed,
        "rainfall": rainfall,
        "lighting": lighting,
        "uv": uv,
        "additional_bytes": info["additional_bytes"],
    }
    
    try:
        hass.bus.async_fire(str(info["device_id"]), event_data)

    except Exception as e:
        logging.error(f"error in firing event for feedback health: {e}")
