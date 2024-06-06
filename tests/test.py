from TISControlProtocol.BytesHelper import build_packet

from TISControlProtocol.Protocols import setup_udp_protocol

# from TISControlProtocol.Protocols import setup_udp_protocol

x = build_packet(
    [0x01, 0x01],
    "1111.111.1.1",
    "11:11:11:11:11:11:11:11",
    "11:11:11:11:11:11:11:11",
    [0x01, 0x01],
    [0x01, 0x01],
    [0x01, 0x01],
)

print(x)
