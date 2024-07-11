from socket import socket, SOL_SOCKET, SO_BROADCAST

from TISControlProtocol.Protocols.udp.AckCoordinator import AckCoordinator
import asyncio
from abc import ABC, abstractmethod
from TISControlProtocol.shared import ack_events  # noqa: F401
import logging


class IPacketSender(ABC):
    @abstractmethod
    async def send_packet(self, packet):
        pass

    @abstractmethod
    async def send_packet_with_ack(
        self,
        packet: list,
        packet_dict: dict = None,
        channel_number: int = None,
        attempts: int = 3,
        timeout: float = 5.0,
    ):
        pass


# PacketSender.py
class PacketSender:
    def __init__(self, socket: socket, coordinator: AckCoordinator, UDP_IP, UDP_PORT):
        self.UDP_IP = UDP_IP
        self.UDP_PORT = UDP_PORT
        self.socket = socket
        self.socket.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
        self.coordinator = coordinator
        self.command_stacks = {}  # Holds the command stacks
        self.last_command_times = {}  # Holds the last command times for debouncing

    async def send_packet(self, packet: list):
        print(f"sending {packet}")
        self.socket.sendto(bytes(packet), (self.UDP_IP, self.UDP_PORT))

    async def send_packet_with_ack(
        self,
        packet: list,
        packet_dict: dict = None,
        channel_number: int = None,
        attempts: int = 10,
        timeout: float = 0.5,
        debounce_time: float = 0.5,  # The debounce time in seconds
    ):
        unique_id = (
            tuple(packet_dict["device_id"]),
            tuple(packet_dict["operation_code"]),
            channel_number,
        )

        # Add the command to the stack for this unique ID
        if unique_id not in self.command_stacks:
            self.command_stacks[unique_id] = []
        self.command_stacks[unique_id].append(packet)

        # Only process the last command in the stack
        if packet != self.command_stacks[unique_id][-1]:
            return

        # If the command is being called too quickly after the last one, ignore it
        if (
            unique_id in self.last_command_times
            and asyncio.get_event_loop().time() - self.last_command_times[unique_id]
            < debounce_time
        ):
            return

        self.last_command_times[unique_id] = asyncio.get_event_loop().time()

        event = self.coordinator.create_ack_event(unique_id)

        for attempt in range(attempts):
            await self.send_packet(packet)
            try:
                await asyncio.wait_for(event.wait(), timeout)
                logging.error(f"ack received for {unique_id}")
                # Remove the command from the stack after it's processed
                self.command_stacks[unique_id].remove(packet)
                return True
            except asyncio.TimeoutError:
                print(
                    f"ack not received within {timeout} seconds, attempt {attempt + 1}"
                )
                logging.error(f"ack not received within {timeout} seconds")

        self.coordinator.remove_ack_event(unique_id)
        logging.error(f"ack not received after {attempts} attempts")
        return False

    async def brodcast_packet(self, packet: list):
        print(f"broadcasting {packet}")
        self.socket.sendto(bytes(packet), ("<broadcast>", self.UDP_PORT))
