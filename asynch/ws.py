from urllib import parse

from channels.generic.websocket import AsyncWebsocketConsumer
from asynch.client import DeviceClient
from asynch.constants import sc_control_msg_type
from asynch.serializers import ReceiveMsgObj, format_get_clipboard_data, format_set_clipboard_data


class DeviceWebsocketConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.device_id = None
        self.query_params = None
        self.device_client = None

    async def connect(self):
        await self.accept()
        # 1.获取请求参数
        self.query_params = parse.parse_qs(self.scope['query_string'].decode())
        self.device_id = self.scope['url_route']['kwargs']['device_id'].replace(',', '.').replace('_', ':')
        # 2.获取当前ws_client对应的 device_client
        self.device_client = DeviceClient(self)
        await self.device_client.start()

    async def receive(self, text_data=None, bytes_data=None):
        """receive used to control device"""
        if not self.device_client.scrcpy_kwargs['control']:
            return
        obj = ReceiveMsgObj()
        obj.format_text_data(text_data)
        # keycode
        if obj.msg_type == sc_control_msg_type.SC_CONTROL_MSG_TYPE_INJECT_KEYCODE:
            if obj.action is None:
                await self.device_client.controller.inject_keycode(obj.keycode, action=0)
                await self.device_client.controller.inject_keycode(obj.keycode, action=1)
            else:
                await self.device_client.controller.inject_keycode(obj.keycode, action=obj.action)
        # text
        elif obj.msg_type == sc_control_msg_type.SC_CONTROL_MSG_TYPE_INJECT_TEXT:
            await self.device_client.controller.inject_text(obj.text)
        # touch
        elif obj.msg_type == sc_control_msg_type.SC_CONTROL_MSG_TYPE_INJECT_TOUCH_EVENT:
            await self.device_client.controller.inject_touch_event(x=obj.x, y=obj.y, resolution=obj.resolution, action=obj.action)
        # scroll
        elif obj.msg_type == sc_control_msg_type.SC_CONTROL_MSG_TYPE_INJECT_SCROLL_EVENT:
            await self.device_client.controller.inject_scroll_event(x=obj.x, y=obj.y, distance_x=obj.distance_x, distance_y=obj.distance_y, resolution=obj.resolution)
        # back_or_screen_on
        elif obj.msg_type == sc_control_msg_type.SC_CONTROL_MSG_TYPE_BACK_OR_SCREEN_ON:
            if not obj.action:
                await self.device_client.controller.back_or_screen_on(action=0)
                await self.device_client.controller.back_or_screen_on(action=1)
            else:
                await self.device_client.controller.back_or_screen_on(action=obj.action)
        # get_clipboard
        elif obj.msg_type == sc_control_msg_type.SC_CONTROL_MSG_TYPE_GET_CLIPBOARD:
            data = await self.device_client.controller.get_clipboard(copy_key=obj.copy_key)
            await self.send(bytes_data=format_get_clipboard_data(data))
        # set_clipboard
        elif obj.msg_type == sc_control_msg_type.SC_CONTROL_MSG_TYPE_SET_CLIPBOARD:
            data = await self.device_client.controller.set_clipboard(text=obj.text, sequence=obj.sequence, paste=obj.paste)
            await self.send(bytes_data=format_set_clipboard_data(data))
        # set_screen_power_mode
        elif obj.msg_type == sc_control_msg_type.SC_CONTROL_MSG_TYPE_SET_SCREEN_POWER_MODE:
            await self.device_client.controller.set_screen_power_mode(obj.screen_power_mode)
        # swipe
        elif obj.msg_type == sc_control_msg_type.SC_CONTROL_MSG_TYPE_INJECT_SWIPE_EVENT:
            await self.device_client.controller.swipe(x=obj.x, y=obj.y, end_x=obj.end_x, end_y=obj.end_y, resolution=obj.resolution, unit=obj.unit, delay=obj.delay)
        # update resolution
        elif obj.msg_type == 999:
            self.device_client.resolution = obj.resolution

    async def disconnect(self, code):
        await self.device_client.stop()
