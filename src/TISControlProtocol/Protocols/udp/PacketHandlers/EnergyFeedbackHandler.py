from homeassistant.core import HomeAssistant
import struct
import logging


def big_endian_to_num(str_list):
    logging.error(f"big endian to num ( {str_list} )")
    big_endian = "".join(str(hex(x)) for x in str_list)
    logging.error(f"big_endian: {big_endian}")
    value = struct.unpack(">f", bytes.fromhex(big_endian))[0]
    logging.error(f"value: {value}")
    return round(value, 1)


async def handle_energy_feedback(hass: HomeAssistant, info: dict):
    """
    Handle the feedback from an energy sensor.
    """
    device_id = info["device_id"]
    channel_num = int(info["additional_bytes"][0]) + 1
    sub_operation = int(info["additional_bytes"][1])
    logging.warning(f"info {info} ,, sub_operation {sub_operation}")

    if sub_operation == 0xDA:
        # [energy, monthly power, phase1, phase2, phase3]
        energy = int(
            (info["additional_bytes"][16] << 8) | (info["additional_bytes"][17])
        )

        event_data = {
            "device_id": device_id,
            "channel_num": channel_num,
            "feedback_type": "monthly_energy_feedback",
            "energy": energy,
            "additional_bytes": info["additional_bytes"],
        }

        try:
            hass.bus.async_fire(str(info["device_id"]), event_data)
        except Exception as e:
            logging.error(f"error in firing event for feedback: {e}")
    elif sub_operation == 0x65:
        logging.error(f"energy 0x65 packet: {info['additional_bytes']}")

        try:
            logging.warning(f"v1: {(big_endian_to_num(info['additional_bytes'][3:7]))}")
            logging.warning(
                f"v2: {(big_endian_to_num(info['additional_bytes'][7:11]))}"
            )
            logging.warning(
                f"v3: {(big_endian_to_num(info['additional_bytes'][11:15]))}"
            )
            logging.warning(
                f"current_p1: {(big_endian_to_num(info['additional_bytes'][15:19]))}"
            )
            logging.warning(
                f"current_p2: {(big_endian_to_num(info['additional_bytes'][19:23]))}"
            )
            logging.warning(
                f"current_p3: {(big_endian_to_num(info['additional_bytes'][23:27]))}"
            )
            logging.warning(
                f"active_p1: {(big_endian_to_num(info['additional_bytes'][27:31]))}"
            )
            logging.warning(
                f"active_p2: {(big_endian_to_num(info['additional_bytes'][31:35]))}"
            )
            logging.warning(
                f"active_p3: {(big_endian_to_num(info['additional_bytes'][35:39]))}"
            )
            logging.warning(
                f"apparent1: {(big_endian_to_num(info['additional_bytes'][39:43]))}"
            )
            logging.warning(
                f"apparent2: {(big_endian_to_num(info['additional_bytes'][43:47]))}"
            )
            logging.warning(
                f"apparent3: {(big_endian_to_num(info['additional_bytes'][47:51]))}"
            )
            logging.warning(
                f"reactive1: {(big_endian_to_num(info['additional_bytes'][51:55]))}"
            )
            logging.warning(
                f"reactive2: {(big_endian_to_num(info['additional_bytes'][55:59]))}"
            )
            logging.warning(
                f"reactive3: {(big_endian_to_num(info['additional_bytes'][59:63]))}"
            )
            logging.warning(
                f"pf1: {(big_endian_to_num(info['additional_bytes'][63:67]),)}"
            )
            logging.warning(
                f"pf2: {(big_endian_to_num(info['additional_bytes'][67:71]),)}"
            )
            logging.warning(
                f"pf3: {(big_endian_to_num(info['additional_bytes'][71:75]),)}"
            )
            logging.warning(
                f"pa1: {(big_endian_to_num(info['additional_bytes'][75:79]),)}"
            )
            logging.warning(
                f"pa2: {(big_endian_to_num(info['additional_bytes'][79:83]),)}"
            )
            logging.warning(
                f"pa3: {(big_endian_to_num(info['additional_bytes'][83:87]),)}"
            )
            logging.warning(
                f"avg_live_to_neutral: {(big_endian_to_num(info['additional_bytes'][87:91]),)}"
            )
            logging.warning(
                f"avg_current: {(big_endian_to_num(info['additional_bytes'][91:95]),)}"
            )
            logging.warning(
                f"sum_current: {(big_endian_to_num(info['additional_bytes'][95:99]),)}"
            )
            logging.warning(
                f"total_power: {(big_endian_to_num(info['additional_bytes'][107:111]),)}"
            )
            logging.warning(
                f"total_volt_amps: {(big_endian_to_num(info['additional_bytes'][115:119]),)}"
            )
            logging.warning(
                f"total_var: {(big_endian_to_num(info['additional_bytes'][123:127]),)}"
            )
            logging.warning(
                f"total_pf: {(big_endian_to_num(info['additional_bytes'][127:131]),)}"
            )
            logging.warning(
                f"total_pa: {(big_endian_to_num(info['additional_bytes'][135:139]),)}"
            )
            logging.warning(
                f"frq: {(big_endian_to_num(info['additional_bytes'][143:147]),)}"
            )

            energy = {
                "v1": big_endian_to_num(info["additional_bytes"][3:7]),
                "v2": big_endian_to_num(info["additional_bytes"][7:11]),
                "v3": big_endian_to_num(info["additional_bytes"][11:15]),
                "current_p1": big_endian_to_num(info["additional_bytes"][15:19]),
                "current_p2": big_endian_to_num(info["additional_bytes"][19:23]),
                "current_p3": big_endian_to_num(info["additional_bytes"][23:27]),
                "active_p1": big_endian_to_num(info["additional_bytes"][27:31]),
                "active_p2": big_endian_to_num(info["additional_bytes"][31:35]),
                "active_p3": big_endian_to_num(info["additional_bytes"][35:39]),
                "apparent1": big_endian_to_num(info["additional_bytes"][39:43]),
                "apparent2": big_endian_to_num(info["additional_bytes"][43:47]),
                "apparent3": big_endian_to_num(info["additional_bytes"][47:51]),
                "reactive1": big_endian_to_num(info["additional_bytes"][51:55]),
                "reactive2": big_endian_to_num(info["additional_bytes"][55:59]),
                "reactive3": big_endian_to_num(info["additional_bytes"][59:63]),
                "pf1": big_endian_to_num(info["additional_bytes"][63:67]),
                "pf2": big_endian_to_num(info["additional_bytes"][67:71]),
                "pf3": big_endian_to_num(info["additional_bytes"][71:75]),
                "pa1": big_endian_to_num(info["additional_bytes"][75:79]),
                "pa2": big_endian_to_num(info["additional_bytes"][79:83]),
                "pa3": big_endian_to_num(info["additional_bytes"][83:87]),
                "avg_live_to_neutral": big_endian_to_num(
                    info["additional_bytes"][87:91]
                ),
                "avg_current": big_endian_to_num(info["additional_bytes"][91:95]),
                "sum_current": big_endian_to_num(info["additional_bytes"][95:99]),
                "total_power": big_endian_to_num(info["additional_bytes"][107:111]),
                "total_volt_amps": big_endian_to_num(info["additional_bytes"][115:119]),
                "total_var": big_endian_to_num(info["additional_bytes"][123:127]),
                "total_pf": big_endian_to_num(info["additional_bytes"][127:131]),
                "total_pa": big_endian_to_num(info["additional_bytes"][135:139]),
                "frq": big_endian_to_num(info["additional_bytes"][143:147]),
            }

            event_data = {
                "device_id": device_id,
                "channel_num": channel_num,
                "feedback_type": "energy_feedback",
                "energy": energy,
                "additional_bytes": info["additional_bytes"],
            }

            hass.bus.async_fire(str(info["device_id"]), event_data)
            logging.error(f"event got fired {info['additional_bytes']}")
        except Exception as e:
            logging.error(f"error in firing event for feedback: {e}")
