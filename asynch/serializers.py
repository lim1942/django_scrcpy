import json

from asynch.constants import sc_copy_key, sc_screen_power_mode


class ReceiveMsgObj:
    def __init__(self):
        self.msg_type = None
        # used for [inject_keycode][touch][back_or_screen_on]  0 down, 1 up, 2 move
        self.action = None
        # used for [inject_keycode]
        self.keycode = None
        self.repeat = None
        # used for [inject_text][set_clipboard]
        self.text = None
        # used for [touch][scroll]
        self.resolution = None
        self.x = None
        self.y = None
        # used for [scroll]
        self.distance_x = None
        self.distance_y = None
        # used for [get_clipboard]
        self.copy_key = sc_copy_key.SC_COPY_KEY_COPY
        # used for [set_clipboard]
        self.sequence = 1
        self.paste = True
        # used for [set_screen_power_mode]
        self.screen_power_mode = sc_screen_power_mode.SC_SCREEN_POWER_MODE_NORMAL
        # used for [swipe]
        self.end_x = None
        self.end_y = None
        self.unit = 5
        self.delay = 0.005

    def format_text_data(self, data):
        data_dict = json.loads(data)
        self.msg_type = data_dict['msg_type']
        for k, v in data_dict.items():
            setattr(self, k, v)


# b'\x00\x00\x00\x01' start is video stream, so b'\x00\x00\x00\x02' for other msg
# b'\x00\x00\x00\x02\x00' get_clipboard_data
def format_get_clipboard_data(data):
    return b'\x00\x00\x00\x02\x00' + data


# b'\x00\x00\x00\x02\x01' set_clipboard_data
def format_set_clipboard_data(data):
    return b'\x00\x00\x00\x02\x01' + data
