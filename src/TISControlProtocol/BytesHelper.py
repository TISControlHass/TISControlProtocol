import binascii
from TISControlProtocol.crc import checkCRC, packCRC


def bytes2hex(data, rtype=[]):
    """A helper function to parse bytes to hex

    :param data: the raw bytes array
    :type data: bytes array
    :param rtype: determine return type whether list of ints or single hex str, defaults to []
    :type rtype: list, optional
    :return: list of ints or hex string
    :rtype: list | str
    """
    hex_string = binascii.hexlify(data).decode()
    hex_list = [int(hex_string[i : i + 2], 16) for i in range(0, len(hex_string), 2)]
    if isinstance(rtype, list):
        return hex_list
    else:
        return hex_string


def build_packet(
    operation_code: list,
    ip_address: str,
    destination_mac: str = "AA:AA:AA:AA:AA:AA:AA:AA",
    source_mac: str = "CB:CB:CB:CB:CB:CB:CB:CB",
    device_id: list = [],
    source_device_id: list = [0x01, 0xFE],
    additional_packets: list = [],
    header="SMARTCLOUD",
):

    # test if all params are loaded
    ip_bytes = [int(part) for part in ip_address.split(".")]
    header_bytes = [ord(char) for char in header]
    source_mac = [int(part, 16) for part in source_mac.split(":")]
    destination_mac = [int(part, 16) for part in destination_mac.split(":")]
    # TODO: modify length
    # length = 21 + len(additional_packets)
    length = 11 + len(additional_packets)
    packet = (
        ip_bytes
        + header_bytes
        + [0xAA, 0xAA]
        + [length]
        # + source_mac
        + source_device_id
        + [0xFF, 0xFE]
        + operation_code
        # + destination_mac
        + device_id
        + additional_packets
    )
    packet = packCRC(packet)
    return packet


def decode_mac(mac: list):
    return ":".join([f"{byte:02X}" for byte in mac])


def int_to_8_bit_binary(number):
    binary_string = bin(number)[2:]
    return binary_string.zfill(8)[::-1]
