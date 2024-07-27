"""Class for handling the UDP protocol"""

from ...BytesHelper import build_packet
from typing import List


class TISPacket:
    """
    Class representing a Packet.

    :param device_id: List of integers representing the device ID.
    :param operation_code: List of integers representing the operation code.
    :param source_ip: Source IP address as a string.
    :param destination_ip: Destination IP address as a string.
    :param additional_bytes: Optional list of additional bytes.
    """

    def __init__(
        self,
        device_id: List[int],
        operation_code: List[int],
        source_ip: str,
        destination_ip: str,
        additional_bytes: List[int] = None,
    ):
        if additional_bytes is None:
            additional_bytes = []
        self.device_id = device_id
        self.operation_code = operation_code
        self.source_ip = source_ip
        self.destination_ip = destination_ip
        self.additional_bytes = additional_bytes
        self._packet = build_packet(
            ip_address=self.source_ip,
            device_id=self.device_id,
            operation_code=self.operation_code,
            additional_packets=self.additional_bytes,
        )

    def __str__(self) -> str:
        return f"Packet: {self._packet}"

    def __repr__(self) -> str:
        return f"Packet: {self._packet}"

    def __bytes__(self) -> bytes:
        return bytes(self._packet)


class ProtocolHandler:
    OPERATION_CONTROL = [0x00, 0x31]
    OPERATION_CONTROL_UPDATE = [0x00, 0x33]

    def __init__(self) -> None:
        """Initialize a ProtocolHandler instance."""
        pass

    def generate_control_on_packet(self, entity) -> TISPacket:
        """
        Generate a packet to switch on the device.

        :param entity: The entity object containing device information.
        :return: A Packet instance.
        """
        return TISPacket(
            device_id=entity.device_id,
            operation_code=ProtocolHandler.OPERATION_CONTROL,
            source_ip=entity.api.host,
            destination_ip=entity.gateway,
            additional_bytes=[entity.channel_number, 0x64, 0x00, 0x00],
        )

    def generate_control_off_packet(self, entity) -> TISPacket:
        """
        Generate a packet to switch off the device.

        :param entity: The entity object containing device information.
        :return: A Packet instance.
        """
        return TISPacket(
            device_id=entity.device_id,
            operation_code=ProtocolHandler.OPERATION_CONTROL,
            source_ip=entity.api.host,
            destination_ip=entity.gateway,
            additional_bytes=[entity.channel_number, 0x00, 0x00, 0x00],
        )

    def generate_control_update_packet(self, entity) -> TISPacket:
        """
        Generate a packet to update the device control.

        :param entity: The entity object containing device information.
        :return: A Packet instance.
        """
        return TISPacket(
            device_id=entity.device_id,
            operation_code=ProtocolHandler.OPERATION_CONTROL_UPDATE,
            source_ip=entity.api.host,
            destination_ip=entity.gateway,
            additional_bytes=[],
        )
