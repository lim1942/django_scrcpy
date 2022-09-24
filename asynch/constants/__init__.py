# ================================
# sc_control_msg_type
# ================================
class sc_control_msg_type:
    SC_CONTROL_MSG_TYPE_INJECT_KEYCODE = 0
    SC_CONTROL_MSG_TYPE_INJECT_TEXT = 1
    SC_CONTROL_MSG_TYPE_INJECT_TOUCH_EVENT = 2
    SC_CONTROL_MSG_TYPE_INJECT_SCROLL_EVENT = 3
    SC_CONTROL_MSG_TYPE_BACK_OR_SCREEN_ON = 4
    SC_CONTROL_MSG_TYPE_EXPAND_NOTIFICATION_PANEL = 5
    SC_CONTROL_MSG_TYPE_EXPAND_SETTINGS_PANEL = 6
    SC_CONTROL_MSG_TYPE_COLLAPSE_PANELS = 7
    SC_CONTROL_MSG_TYPE_GET_CLIPBOARD = 8
    SC_CONTROL_MSG_TYPE_SET_CLIPBOARD = 9
    SC_CONTROL_MSG_TYPE_SET_SCREEN_POWER_MODE = 10
    SC_CONTROL_MSG_TYPE_ROTATE_DEVICE = 11
    SC_CONTROL_MSG_TYPE_INJECT_SWIPE_EVENT = 30


# ================================
# sc_screen_power_mode
# ================================
class sc_screen_power_mode:
    SC_SCREEN_POWER_MODE_OFF = 0
    SC_SCREEN_POWER_MODE_NORMAL = 2


# ================================
# sc_copy_key
# ================================
class sc_copy_key:
    SC_COPY_KEY_NONE = 0
    SC_COPY_KEY_COPY = 1
    SC_COPY_KEY_CUT = 2
