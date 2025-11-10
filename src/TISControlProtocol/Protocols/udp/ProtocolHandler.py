"""Class for handling the UDP protocol"""

from ...BytesHelper import build_packet
from typing import List, Literal, Tuple


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
    OPERATION_GET_TEMP = [0xE3, 0xE7]
    OPERATION_GET_HEALTH = [0x20, 0x24]
    OPERATION_DISCOVERY = [0x00, 0x0E]
    OPERATION_CONTROL_SECURITY = [0x01, 0x04]
    OPERATION_CONTROL_AC = [0xE0, 0xEE]
    OPERATION_AC_UPDATE = [0xE0, 0xEC]
    OPERATION_FLOOR_UPDATE = [0x19, 0x44]
    OPERATION_FLOOR_CONTROL = [0xE3, 0xD8]
    OPERATION_GET_WEATHER = [0x20, 0x20]
    OPERATION_SECURITY_UPDATE = [0x01, 0x1E]
    OPERATION_ANALOG_UPDATE = [0xEF, 0x00]
    OPERATION_ENERGY_UPDATE = [0x20, 0x10]
    OPERATION_UNIVERSAL_SWITCH = [0xE0, 0x1C]

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

    def generate_temp_sensor_update_packet(self, entity) -> TISPacket:
        """
        Generate a packet to update the temperature sensor.

        :param entity: The entity object containing device information.
        :return: A Packet instance.
        """
        return TISPacket(
            device_id=entity.device_id,
            operation_code=TISProtocolHandler.OPERATION_GET_TEMP,
            source_ip=entity.api.host,
            destination_ip=entity.gateway,
            additional_bytes=[0x00],
        )

    def generate_health_sensor_update_packet(self, entity) -> TISPacket:
        """
        Generate a packet to update the health sensor.

        :param entity: The entity object containing device information.
        :return: A Packet instance.
        """
        return TISPacket(
            device_id=entity.device_id,
            operation_code=TISProtocolHandler.OPERATION_GET_HEALTH,
            source_ip=entity.api.host,
            destination_ip=entity.gateway,
            additional_bytes=[0x14, 0x00],
        )

    def generate_weather_sensor_update_packet(self, entity) -> TISPacket:
        """
        Generate a packet to update the weather sensor.

        :param entity: The entity object containing device information.
        :return: A Packet instance.
        """
        return TISPacket(
            device_id=entity.device_id,
            operation_code=TISProtocolHandler.OPERATION_GET_WEATHER,
            source_ip=entity.api.host,
            destination_ip=entity.gateway,
            additional_bytes=[0x4, 0x00],
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

    def generate_rgbw_light_control_packet(
        self, entity, color: Tuple[int, int, int, int]
    ) -> Tuple[TISPacket]:
        """
        Generate packets to control an RGBW light.
        :param entity: The entity object containing device information.
        :param color: A tuple of integers representing the RGBW color.
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
            TISPacket(
                device_id=entity.device_id,
                operation_code=TISProtocolHandler.OPERATION_CONTROL,
                source_ip=entity.api.host,
                destination_ip=entity.gateway,
                additional_bytes=[entity.w_channel, color[3], 0x00, 0x00],
            ),
        )

    def generate_no_pos_cover_packet(
        self, entity, mode: Literal["open", "close", "stop"]
    ) -> tuple[TISPacket, TISPacket]:
        if mode == "open":
            return (
                TISPacket(
                    device_id=entity.device_id,
                    operation_code=TISProtocolHandler.OPERATION_CONTROL,
                    source_ip=entity.api.host,
                    destination_ip=entity.gateway,
                    additional_bytes=[entity.up_channel_number, 0x64, 0x00, 0x00],
                ),
                TISPacket(
                    device_id=entity.device_id,
                    operation_code=TISProtocolHandler.OPERATION_CONTROL,
                    source_ip=entity.api.host,
                    destination_ip=entity.gateway,
                    additional_bytes=[entity.down_channel_number, 0x00, 0x00, 0x00],
                ),
            )
        elif mode == "close":
            return (
                TISPacket(
                    device_id=entity.device_id,
                    operation_code=TISProtocolHandler.OPERATION_CONTROL,
                    source_ip=entity.api.host,
                    destination_ip=entity.gateway,
                    additional_bytes=[entity.up_channel_number, 0x00, 0x00, 0x00],
                ),
                TISPacket(
                    device_id=entity.device_id,
                    operation_code=TISProtocolHandler.OPERATION_CONTROL,
                    source_ip=entity.api.host,
                    destination_ip=entity.gateway,
                    additional_bytes=[entity.down_channel_number, 0x64, 0x00, 0x00],
                ),
            )

        elif mode == "stop":
            return (
                TISPacket(
                    device_id=entity.device_id,
                    operation_code=TISProtocolHandler.OPERATION_CONTROL,
                    source_ip=entity.api.host,
                    destination_ip=entity.gateway,
                    additional_bytes=[entity.up_channel_number, 0x00, 0x00, 0x00],
                ),
                TISPacket(
                    device_id=entity.device_id,
                    operation_code=TISProtocolHandler.OPERATION_CONTROL,
                    source_ip=entity.api.host,
                    destination_ip=entity.gateway,
                    additional_bytes=[entity.down_channel_number, 0x00, 0x00, 0x00],
                ),
            )

    def generate_control_security_packet(self, entity, mode) -> TISPacket:
        """
        Generate a packet to set the security mode.

        vacation=1
        Away=2
        Night=3
        Disarm=6
        """
        return TISPacket(
            device_id=entity.device_id,
            operation_code=TISProtocolHandler.OPERATION_CONTROL_SECURITY,
            source_ip=entity.api.host,
            destination_ip=entity.gateway,
            additional_bytes=[entity.channel_number, mode],
        )

    def generate_update_security_packet(self, entity) -> TISPacket:
        """
        Generate a packet to set request security update.
        """
        return TISPacket(
            device_id=entity.device_id,
            operation_code=TISProtocolHandler.OPERATION_SECURITY_UPDATE,
            source_ip=entity.api.host,
            destination_ip=entity.gateway,
            additional_bytes=[entity.channel_number],
        )

    def generate_ac_control_packet(
        self,
        entity,
        temperature_ranges: dict,
        fan_modes: dict,
        target_state: str | None = None,
        target_temperature: float | None = None,
        target_mode: str | None = None,  # noqa: F821 # type: ignore
        target_fan_mode: str | None = None,
    ) -> TISPacket:
        # Determine the target values, falling back to class attributes if not provided
        if not target_state:
            if entity._attr_state == "unknown":
                target_state = False
            else:
                target_state = entity._attr_state

        target_temperature = (
            target_temperature
            if target_temperature is not None
            else entity._attr_target_temperature
        )
        target_mode = target_mode if target_mode is not None else entity.hvac_mode
        target_fan_mode = (
            target_fan_mode if target_fan_mode is not None else entity._attr_fan_mode
        )
        # Convert target temperature to byte
        target_temperature_byte = (
            int(target_temperature) if target_temperature else 0x00
        )
        # Construct the additional bytes for the packet
        additional_bytes = [
            entity.ac_number,
            int(target_state == "on"),
            target_temperature_byte,
            int(
                (temperature_ranges[target_mode]["packet_mode_index"] << 4)
                | fan_modes[target_fan_mode]
            ),
            0x01,
            target_temperature_byte,
            target_temperature_byte,
            target_temperature_byte,
            0x00,
        ]

        # Generate and return the packet
        return TISPacket(
            device_id=entity.device_id,
            operation_code=self.OPERATION_CONTROL_AC,
            source_ip=entity.api.host,
            destination_ip=entity.gateway,
            additional_bytes=additional_bytes,
        )

    def generate_ac_update_packet(self, entity) -> TISPacket:
        return TISPacket(
            device_id=entity.device_id,
            operation_code=self.OPERATION_AC_UPDATE,
            source_ip=entity.api.host,
            destination_ip=entity.gateway,
            additional_bytes=[entity.ac_number],
        )

    def generate_floor_update_packet(self, entity) -> TISPacket:
        return TISPacket(
            device_id=entity.device_id,
            operation_code=self.OPERATION_FLOOR_UPDATE,
            source_ip=entity.api.host,
            destination_ip=entity.gateway,
            additional_bytes=[entity.heater_number],
        )

    def generate_floor_on_off_packet(self, entity, state: int) -> TISPacket:

        if entity.heater_number == 0:
            add_bytes=[0x14, state]

        if entity.heater_number == 1:
            add_bytes=[(entity.heater_number + 0x22), 0x14, state]
        
        if entity.heater_number >= 2:
            add_bytes=[0x2E, (entity.heater_number) + 1, 0x03, state]
        
        return TISPacket(
            device_id=entity.device_id,
            operation_code=self.OPERATION_FLOOR_CONTROL,
            source_ip=entity.api.host,
            destination_ip=entity.gateway,
            additional_bytes=add_bytes            
            
        )

    def generate_floor_set_temp_packet(
        self, entity, target_temperature: int
    ) -> TISPacket:
        
        if entity.heater_number == 0:
            add_bytes=[0x18, target_temperature]

        if entity.heater_number == 1:
            add_bytes=[(entity.heater_number + 0x22), 0x18, target_temperature]
        
        if entity.heater_number >= 2:
            add_bytes=[0x2E, (entity.heater_number) + 1, 0x04, target_temperature]
    
        return TISPacket(
            device_id=entity.device_id,
            operation_code=self.OPERATION_FLOOR_CONTROL,
            source_ip=entity.api.host,
            destination_ip=entity.gateway,
            additional_bytes=add_bytes,
        )

    def generate_update_analog_packet(self, entity) -> TISPacket:
        """
        Generate a packet to set request analog update.
        """
        return TISPacket(
            device_id=entity.device_id,
            operation_code=TISProtocolHandler.OPERATION_ANALOG_UPDATE,
            source_ip=entity.api.host,
            destination_ip=entity.gateway,
            additional_bytes=[],
        )

    def generate_update_monthly_energy_packet(self, entity) -> TISPacket:
        """
        Generate a packet to set request energy meter update.
        """
        return TISPacket(
            device_id=entity.device_id,
            operation_code=TISProtocolHandler.OPERATION_ENERGY_UPDATE,
            source_ip=entity.api.host,
            destination_ip=entity.gateway,
            additional_bytes=[entity.channel_number - 1, 0xDA, 0x64],
        )

    def generate_update_energy_packet(self, entity) -> TISPacket:
        """
        Generate a packet to set request energy meter update.
        """
        return TISPacket(
            device_id=entity.device_id,
            operation_code=TISProtocolHandler.OPERATION_ENERGY_UPDATE,
            source_ip=entity.api.host,
            destination_ip=entity.gateway,
            additional_bytes=[entity.channel_number - 1, 0x65],
        )

    def generate_universal_switch_packet(self, entity) -> TISPacket:
        """
        Generate a packet to set request energy meter update.
        """
        return TISPacket(
            device_id=entity.device_id,
            operation_code=TISProtocolHandler.OPERATION_UNIVERSAL_SWITCH,
            source_ip=entity.api.host,
            destination_ip=entity.gateway,
            additional_bytes=[entity.channel_number, entity.universal_type],
        )
