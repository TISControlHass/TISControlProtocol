from TISControlProtocol.BytesHelper import *  # noqa: F403
from TISControlProtocol.Protocols.udp.PacketSender import PacketSender
from TISControlProtocol.Protocols.udp.PacketReceiver import PacketReceiver
from TISControlProtocol.Protocols.udp.AckCoordinator import AckCoordinator

from TISControlProtocol.shared import ack_events

from homeassistant.core import HomeAssistant  # type: ignore
from .PacketHandlers.BinaryFeedbackHandler import handle_binary_feedback
from .PacketHandlers.ControlResponseHandler import handle_control_response

from .PacketHandlers.AutoBinaryFeedbackHandler import handle_auto_binary_feedback

from .PacketHandlers.ClimateControlFeedbackHandler import (
    handle_climate_control_feedback,
)
from .PacketHandlers.ClimateBinaryFeedbackHandler import handle_climate_binary_feedback
from .PacketHandlers.FloorBinaryFeedbackHandler import handle_floor_binary_feedback
from .PacketHandlers.DiscoveryFeedbackHandler import handle_discovery_feedback
from .PacketHandlers.UpdateResponseHandler import handle_update_response
from .PacketHandlers.RealTimeFeedbackHandler import handle_real_time_feedback
from .PacketHandlers.LunaTempFeedbackHandler import handle_luna_temp_feedback
from .PacketHandlers.HealthFeedbackHandler import handle_health_feedback
from .PacketHandlers.SecurityFeedbackHandler import handle_security_feedback


import socket as Socket

OPERATIONS_DICT = {
    (0x00, 0x32): handle_control_response,
    (0xEF, 0xFF): handle_binary_feedback,
    (0xDC, 0x22): handle_auto_binary_feedback,
    (0xE0, 0xEF): handle_climate_control_feedback,
    (0xE0, 0xED): handle_climate_control_feedback,
    (0xE3, 0xD9): handle_climate_binary_feedback,
    (0x19, 0x55): handle_floor_binary_feedback,
    (0x00, 0x0F): handle_discovery_feedback,
    (0x00, 0x34): handle_update_response,
    (0x00, 0x31): handle_real_time_feedback,
    (0xE3, 0xE8): handle_luna_temp_feedback,
    (0x20, 0x25): handle_health_feedback,
    (0x01, 0x05): handle_security_feedback,
}
# 1C 01 30 1B BA DC 22 FF FF 08 02 02 02 02 02 02 02 02 00 01 01 01 01 01 01 01 57 62


class PacketProtocol:
    def __init__(
        self,
        socket: Socket.socket,
        UDP_IP,
        UDP_PORT,
        hass: HomeAssistant,
    ):
        self.UDP_IP = UDP_IP
        self.UDP_PORT = UDP_PORT
        self.socket = socket
        self.searching = False
        self.search_results = []
        self.discovered_devices = []
        self.hass = hass

        self.ack_events = ack_events
        self.coordinator = AckCoordinator()
        self.sender = PacketSender(
            socket=self.socket,
            coordinator=self.coordinator,
            UDP_IP=self.UDP_IP,
            UDP_PORT=self.UDP_PORT,
        )
        self.receiver = PacketReceiver(self.socket, OPERATIONS_DICT, self.hass)

        self.connection_made = self.receiver.connection_made
        self.datagram_received = self.receiver.datagram_received
