from TISControlProtocol.BytesHelper import checkCRC
import logging


# PacketExtractor.py
class PacketExtractor:
    @staticmethod
    def extract_info(packet: list):
        packet_check = checkCRC(packet)
        info = {}
        if packet_check:
            logging.info("correct packet")
            info["source_ip"] = packet[0:4]
            info["device_id"] = packet[17:19]
            info["device_type"] = packet[19:21]
            info["operation_code"] = packet[21:23]
            info["source_device_id"] = packet[23:25]
            info["additional_bytes"] = packet[25:-2]

        else:
            logging.info("wrong packet")
        return info
