from TISControlProtocol.BytesHelper import *
from TISControlProtocol.Protocols.udp.PacketSender import PacketSender
from TISControlProtocol.Protocols.udp.PacketReceiver import PacketReceiver
from TISControlProtocol.Protocols.udp.AckCoordinator import AckCoordinator
from TISControlProtocol.shared import ack_events

from .PacketHandlers.ControlResponseHandler import handle_control_response
from .PacketHandlers.DiscoveryFeedbackHandler import handle_discovery_feedback
from .PacketHandlers.UpdateResponseHandler import handle_update_response

import socket as Socket
from homeassistant.core import HomeAssistant


OPERATIONS_DICT = {
    (0x00, 0x32): handle_control_response,
    (0x00, 0x0F): handle_discovery_feedback,
    (0x00, 0x34): handle_update_response,
}


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
