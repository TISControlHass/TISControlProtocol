import asyncio
from TISControlProtocol.shared import ack_events
from typing import Union
import logging

class AckCoordinator:
    def __init__(self):
        self.ack_events = ack_events

    def create_ack_event(self, unique_id: Union[str, tuple]) -> asyncio.Event:
        logging.info(f"creating ack event for {unique_id}")
        event = asyncio.Event()
        self.ack_events[unique_id] = event
        return event

    def get_ack_event(self, unique_id: Union[str, tuple]) -> Union[asyncio.Event, None]:
        return self.ack_events.get(unique_id)

    def remove_ack_event(self, unique_id: Union[str, tuple]) -> None:
        if unique_id in self.ack_events:
            del self.ack_events[unique_id]

    # async def create_ack_task(
    #     self,
    #     sender,
    #     packet,
    #     packet_dict=None,
    #     channel_number=None,
    #     attempts=3,
    #     timeout=5.0,
    # ) -> bool:
    #     unique_id = (
    #         (tuple(packet_dict["device_id"])),
    #         packet_dict["operation_code"],
    #         channel_number,
    #     )
    #     event = self.create_ack_event(unique_id)

    #     for attempt in range(attempts):
    #         sender.send_packet(packet)
    #         try:
    #             await asyncio.wait_for(event.wait(), timeout)
    #             self.remove_ack_event(unique_id)
    #             return True
    #         except asyncio.TimeoutError:
    #             print(
    #                 f"ack not received within {timeout} seconds, attempt {attempt + 1}"
    #             )

    #     return False
