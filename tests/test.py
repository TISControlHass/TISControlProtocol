from collections import defaultdict
import logging

def _parse_device_manager_request(data: dict) -> None:
    """Parse the device manager request."""
    converted = {
        appliance: {
            "device_id": [int(n) for n in details[0]["device_id"].split(",")],
            "appliance_type": details[0]["appliance_type"].lower().replace(" ", "_"),
            "appliance_class": details[0].get("appliance_class", None),
            "is_protected": bool(int(details[0]["is_protected"])),
            "channels": [
                {
                    "channel_number": int(detail["channel_number"]),
                    "channel_type": detail["channel_type"],
                    "channel_name": detail["channel_name"],
                }
                for detail in details
            ],
        }
        for appliance, details in data["appliances"].items()
        if details[0]["gateway"] == "192.168.1.201"
    }

    grouped = defaultdict(list)
    for appliance, details in converted.items():
        if details["appliance_type"] in ["Switch", "Light"]:
            # logging.error(f"appliance: {appliance}, details: {details}")
            grouped[details["appliance_type"]].append({appliance: details})

    _config_entries = dict(grouped)
    # # add a lock module config entry
    # self._config_entries["lock_module"] = {
    #     "password": data["configs"]["lock_module_password"]
    # }
    # logging.error(f"config_entries stored: {self._config_entries}")
    # # await self.update_entities()
    return _config_entries


test_request = {
    "appliances": {
        "appliance1": [
            {
                "device_id": "1,2",
                "appliance_type": "Light",
                "appliance_class": "classA",
                "is_protected": "1",
                "gateway": "192.168.1.201",
                "channels": [
                    {
                        "channel_number": "1",
                        "channel_type": "type1",
                        "channel_name": "Channel 1",
                    }
                ],
            }
        ]
    },
    "configs": {"lock_module_password": "your_password_here"},
}

out = _parse_device_manager_request(test_request)
logging.info(out)
