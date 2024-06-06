from homeassistant.core import HomeAssistant  # type: ignore


async def handle_discovery_feedback(hass: HomeAssistant, info: dict):
    # check if the record already exists if not add it
    if not any(
        device["device_id"] == info["device_id"]
        for device in hass.data["tis_control"]["discovered_devices"]
    ):
        hass.data["tis_control"]["discovered_devices"].append(info)
