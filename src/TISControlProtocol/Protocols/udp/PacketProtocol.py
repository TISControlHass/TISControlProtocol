from TISControlProtocoll.BytesHelper import *  # noqa: F403
from TISControlProtocoll.Protocols.udp.PacketSender import PacketSender
from TISControlProtocoll.Protocols.udp.PacketReceiver import PacketReceiver
from TISControlProtocoll.Protocols.udp.AckCoordinator import AckCoordinator

from TISControlProtocoll.shared import ack_events

from homeassistant.core import HomeAssistant  # type: ignore
from .PacketHandlers.BinaryFeedbackHandler import handle_binary_feedback
from .PacketHandlers.ControlResponseHandler import handle_control_response

from .PacketHandlers.AutoBinaryFeedbackHandler import handle_auto_binary_feedback

from .PacketHandlers.ClimateFeedbackHandler import handle_climate_feedback
from .PacketHandlers.DiscoveryFeedbackHandler import handle_discovery_feedback

import socket as Socket

OPERATIONS_DICT = {
    (0x00, 0x32): handle_control_response,
    (0xEF, 0xFF): handle_binary_feedback,
    (0xDC, 0x22): handle_auto_binary_feedback,
    (0xE0, 0xED): handle_climate_feedback,
    (0x00, 0x0F): handle_discovery_feedback,
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
