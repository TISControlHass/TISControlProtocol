from TISControlProtocoll.BytesHelper import checkCRC


# PacketExtractor.py
class PacketExtractor:
    @staticmethod
    def extract_info(packet: list):
        packet_check = checkCRC(packet)
        info = {}
        if packet_check:
            print("correct packet")
            info["device_id"] = packet[17:19]
            info["device_type"] = packet[19:21]
            info["operation_code"] = packet[21:23]
            info["additional_bytes"] = packet[25:-2]

        else:
            print("wrong packet")
        return info
