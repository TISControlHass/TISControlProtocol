"""Class for handling the UDP protocol"""

from ...BytesHelper import build_packet
from typing import List, Tuple


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


class TISProtocolHandler:
    OPERATION_CONTROL = [0x00, 0x31]
    OPERATION_CONTROL_UPDATE = [0x00, 0x33]
    OPERATION_GET_LUNA_TEMP = [0xE3, 0xE7]
    OPERATION_DISCOVERY = [0x00, 0x0E]

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
            operation_code=TISProtocolHandler.OPERATION_CONTROL,
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
            operation_code=TISProtocolHandler.OPERATION_CONTROL,
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
            operation_code=TISProtocolHandler.OPERATION_CONTROL_UPDATE,
            source_ip=entity.api.host,
            destination_ip=entity.gateway,
            additional_bytes=[],
        )

    def generate_luna_temp_sensor_update_packet(self, entity) -> TISPacket:
        """
        Generate a packet to update the temperature sensor.

        :param entity: The entity object containing device information.
        :return: A Packet instance.
        """
        return TISPacket(
            device_id=entity.device_id,
            operation_code=TISProtocolHandler.OPERATION_GET_LUNA_TEMP,
            source_ip=entity.api.host,
            destination_ip=entity.gateway,
            additional_bytes=[0x00],
        )

    def generate_discovery_packet(self) -> TISPacket:
        """
        Generate a packet to discover devices on the network.

        :return: A Packet instance.
        """
        return TISPacket(
            device_id=[0xFF, 0xFF],
            operation_code=TISProtocolHandler.OPERATION_DISCOVERY,
            source_ip="0.0.0.0",
            destination_ip="0.0.0.0",
            additional_bytes=[],
        )

    def generate_light_control_packet(self, entity, brightness: int) -> TISPacket:
        """
        Generate packets to control a light.
        :param entity: The entity object containing device information.
        :param brightness: An integer representing the brightness level.
        :return: A Packet instance.
        """
        return TISPacket(
            device_id=entity.device_id,
            operation_code=TISProtocolHandler.OPERATION_CONTROL,
            source_ip=entity.api.host,
            destination_ip=entity.gateway,
            additional_bytes=[entity.channel_number, brightness, 0x00, 0x00],
        )

    def generate_rgb_light_control_packet(
        self, entity, color: Tuple[int, int, int]
    ) -> Tuple[TISPacket]:
        """
        Generate packets to control an RGB light.
        :param entity: The entity object containing device information.
        :param color: A tuple of integers representing the RGB color.
        :return: A tuple of Packet instances.
        """
        return (
            TISPacket(
                device_id=entity.device_id,
                operation_code=TISProtocolHandler.OPERATION_CONTROL,
                source_ip=entity.api.host,
                destination_ip=entity.gateway,
                additional_bytes=[entity.r_channel, color[0], 0x00, 0x00],
            ),
            TISPacket(
                device_id=entity.device_id,
                operation_code=TISProtocolHandler.OPERATION_CONTROL,
                source_ip=entity.api.host,
                destination_ip=entity.gateway,
                additional_bytes=[entity.g_channel, color[1], 0x00, 0x00],
            ),
            TISPacket(
                device_id=entity.device_id,
                operation_code=TISProtocolHandler.OPERATION_CONTROL,
                source_ip=entity.api.host,
                destination_ip=entity.gateway,
                additional_bytes=[entity.b_channel, color[2], 0x00, 0x00],
            ),
        )
