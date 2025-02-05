import logging

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
        logging.error(f"No appliances found for key {(device_id,channel)}")
        return None
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return None
