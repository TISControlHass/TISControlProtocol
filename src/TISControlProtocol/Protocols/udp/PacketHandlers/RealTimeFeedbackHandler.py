from homeassistant.core import HomeAssistant

import logging
import asyncio
from TISControlProtocol.shared import ack_events


async def handle_real_time_feedback(hass: HomeAssistant, info: dict):
    channel_number = info["additional_bytes"][0]
    # await target_appliance.handle_packet(info["additional_bytes"], "control")
    if info["source_device_id"] == [0x64, 0x64]:
        event_data = {
            "device_id": info["device_id"],
            "channel_number": channel_number,
            "feedback_type": "realtime_feedback",
            "additional_bytes": info["additional_bytes"],
        }
        try:
            hass.bus.async_fire(str(info["device_id"]), event_data)
        except Exception as e:
            logging.error(f"error in firing event for feedback: {e}")

    # try:
    #     event: asyncio.Event = ack_events.get(
    #         (
    #             tuple(info["device_id"]),
    #             (0x00, 0x31),
    #             channel_number,
    #         )
    #     )
    #     if event is not None:
    #         print("setting event")
    #         event.set()
    # except Exception as e:
    #     print(e)
