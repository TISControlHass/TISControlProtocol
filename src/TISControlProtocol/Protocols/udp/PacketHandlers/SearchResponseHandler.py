import logging

# deprecated
async def handle_search_response(self, info: dict):
    logging.info(f"got search response packet from {info['device_id']}")
    self.discovered_devices.append(
        {
            "device_id": info["device_id"],
            "device_type": DEVICES_DICT[  # noqa: F821  # type: ignore
                tuple(info["additional_bytes"])
            ],
            "gateway": info["source_ip"],
        }
    )
