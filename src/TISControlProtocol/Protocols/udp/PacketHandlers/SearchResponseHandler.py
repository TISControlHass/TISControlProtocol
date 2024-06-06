
async def handle_search_response(self, info: dict):
    print(f"got search response packet from {info['device_id']}")
    self.discovered_devices.append(
        {
            "mac": info["device_id"],
            "device_type": DEVICES_DICT[tuple(info["additional_bytes"])],
        }
    )
