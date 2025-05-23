from homeassistant.core import HomeAssistant
import logging

#TODO get a way to set 4 sensors together
async def handle_energy_feedback(hass: HomeAssistant, info: dict):
    """
    Handle the feedback from an energy sensor.
    """
    device_id = info["device_id"]
    channel_num = int(info["additional_bytes"][0]) + 1
    sub_operation = int(info["additional_bytes"][1])

    if sub_operation == 0xDA:
        #[energy, mounthly power, phase1, phase2, phase3]
        energy = [int((info["additional_bytes"][12]<<8)|(info["additional_bytes"][13])),
                  int((info["additional_bytes"][16]<<8)|(info["additional_bytes"][17])),
                  int((info["additional_bytes"][6]<<8)|(info["additional_bytes"][7])),
                  int((info["additional_bytes"][8]<<8)|(info["additional_bytes"][9])),
                  int((info["additional_bytes"][10]<<8)|(info["additional_bytes"][11]))]

        event_data = {
            "device_id": device_id,
            "channel_num": channel_num,
            "feedback_type": "energy_feedback",
            "energy": energy,
            "additional_bytes": info["additional_bytes"],
        }

        try:
            hass.bus.async_fire(str(info["device_id"]), event_data)
        except Exception as e:
            logging.error(f"error in firing event for feedback: {e}")
