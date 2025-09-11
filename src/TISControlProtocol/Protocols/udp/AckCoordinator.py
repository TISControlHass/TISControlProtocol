import logging
import asyncio
from TISControlProtocol.shared import ack_events
from typing import Union


class AckCoordinator:
    def __init__(self):
        self.ack_events = ack_events

    def create_ack_event(self, unique_id: Union[str, tuple]) -> asyncio.Event:
        logging.error(f"creating ack event for {unique_id}")
        event = asyncio.Event()
        self.ack_events[unique_id] = event
        return event

    def get_ack_event(self, unique_id: Union[str, tuple]) -> Union[asyncio.Event, None]:
        return self.ack_events.get(unique_id)

    def remove_ack_event(self, unique_id: Union[str, tuple]) -> None:
        if unique_id in self.ack_events:
            del self.ack_events[unique_id]
