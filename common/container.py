from threading import Lock

# for scrcpy deploy process
SCRCPY_PROCESS_DICT = {}

# for wserver
LOCAL_CLIENT_DICT = {}

VIDEO_CLIENT_DICT = {}
VIDEO_CLIENT_DICT_LOCK = Lock()
def modify_video_client_dict(device_id, client, add=True):
    with VIDEO_CLIENT_DICT_LOCK:
        VIDEO_CLIENT_DICT[device_id] = VIDEO_CLIENT_DICT.get(device_id, [])
        if add:
            VIDEO_CLIENT_DICT[device_id].append(client)
        else:
            VIDEO_CLIENT_DICT[device_id].remove(client)

CONTROL_CLIENT_DICT = {}
CONTROL_CLIENT_DICT_LOCK = Lock()
def modify_control_client_dict(device_id, client, add=True):
    with CONTROL_CLIENT_DICT_LOCK:
        CONTROL_CLIENT_DICT[device_id] = CONTROL_CLIENT_DICT.get(device_id, [])
        if add:
            CONTROL_CLIENT_DICT[device_id].append(client)
        else:
            CONTROL_CLIENT_DICT[device_id].remove(client)

