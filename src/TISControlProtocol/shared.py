import logging
import aiofiles
import os
from typing import Optional

appliances_dict = {}
mqtt_appliances_dict = {}
ack_events = {}
loggers = {}


def get_appliance(device_id: tuple, channel: tuple, appliances_dict: dict):
    # appliance key form is ((device_id),(channels))
    try:
        device_appliances = [
            a
            for k, a in appliances_dict.items()
            if k[0] == device_id and channel in k[1]
        ]
        return tuple(device_appliances)[0]
    except IndexError:
        logging.error(f"No appliances found for key {(device_id, channel)}")
        return None
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return None


async def _read_mac(interface: str) -> Optional[str]:
    path = f"/sys/class/net/{interface}/address"
    if not os.path.isfile(path):
        return None

    try:
        async with aiofiles.open(path, "r") as f:
            return (await f.read()).strip().upper()
    except OSError:
        return None


async def get_real_mac(interface: str = "end0") -> Optional[str]:
    """
    Return MAC address for the given interface.

    Fallback order if the interface does not exist:
    1. eth0
    2. wlan0
    3. first available interface
    """
    sys_net = "/sys/class/net"

    if not os.path.isdir(sys_net):
        return None

    interfaces = sorted(os.listdir(sys_net))
    if not interfaces:
        return None

    candidates = [interface, "eth0", "wlan0"]
    candidates.extend(i for i in interfaces if i not in candidates)

    for iface in candidates:
        mac = await _read_mac(iface)
        if mac:
            return mac

    return None
