from TISControlProtocol.BytesHelper import *  # noqa: F403
from socket import socket
from TISControlProtocol.Protocols.udp.PacketExtractor import PacketExtractor
from TISControlProtocol.Protocols.udp.PacketDispatcher import PacketDispatcher
import logging
from homeassistant.core import HomeAssistant  # type: ignore


# PacketReceiver.py
class PacketReceiver:
    def __init__(
        self,
        socket: socket,
        OPERATIONS_DICT: dict,
        hass: HomeAssistant,
    ):
        self.socket = socket
        self._hass = hass
        self.dispatcher = PacketDispatcher(self._hass, OPERATIONS_DICT)
        self.transport = None
        self

    def connection_made(self, transport):
        self.transport = transport
        logging.info("connection made")

    def datagram_received(self, data, addr):
        try:
            hex = bytes2hex(data, [])  # noqa: F405
            info = PacketExtractor.extract_info(hex)
            # dispatch the packet to the appropriate method according to the info
            self._hass.async_create_task(self.dispatcher.dispatch_packet(info))

        except Exception as e:
            logging.error(f"Error in datagram_received: {e}, info: {info}")
