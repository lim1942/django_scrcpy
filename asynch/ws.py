import json
from urllib import parse

from channels.generic.websocket import AsyncWebsocketConsumer
from asynch.client import DeviceClient
from asynch.constants import sc_control_msg_type


class DeviceWebsocketConsumer(AsyncWebsocketConsumer):
    DEVICE_CLIENT_DICT = dict()

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
        # 2.获取当前ws_client对应的device_client
        config_dict = json.loads(self.query_params['config'][0])
        old_device_client = self.DEVICE_CLIENT_DICT.get(self.device_id, None)
        if old_device_client:
            self.device_client = old_device_client
            self.device_client.update(**config_dict)
        else:
            self.device_client = self.DEVICE_CLIENT_DICT[self.device_id] = DeviceClient(self.device_id, **config_dict)
        # 3.记录当前client到CLIENT_DICT
        self.device_client.ws_client_list.append(self)
        # 4.重新开始连接device,重新开始任务
        async with self.device_client.device_lock:
            await self.device_client.stop()
            await self.device_client.start()

    async def receive(self, text_data=None, bytes_data=None):
        """receive used to control device"""
        msg_type = int(text_data[:2])
        msg_data = text_data[2:]
        # keycode
        if msg_type == sc_control_msg_type.SC_CONTROL_MSG_TYPE_INJECT_KEYCODE:
            keycode = int(msg_data)
            await self.device_client.controller.inject_keycode(keycode)
            await self.device_client.controller.inject_keycode(keycode, 1)
        # text
        elif msg_type == sc_control_msg_type.SC_CONTROL_MSG_TYPE_INJECT_TEXT:
            await self.device_client.controller.inject_text(msg_data)
        # touch
        elif msg_type == sc_control_msg_type.SC_CONTROL_MSG_TYPE_INJECT_TOUCH_EVENT:
            x, y = msg_data.split(',')
            await self.device_client.controller.inject_touch_event(int(x), int(y))
            await self.device_client.controller.inject_touch_event(int(x), int(y), 1)
        # scroll
        elif msg_type == sc_control_msg_type.SC_CONTROL_MSG_TYPE_INJECT_SCROLL_EVENT:
            await self.device_client.controller.inject_scroll_event(160, 300, 0, -10)
        # back_or_screen_on
        elif msg_type == sc_control_msg_type.SC_CONTROL_MSG_TYPE_BACK_OR_SCREEN_ON:
            await self.device_client.controller.back_or_screen_on()
            await self.device_client.controller.back_or_screen_on(1)
        # get_clipboard
        elif msg_type == sc_control_msg_type.SC_CONTROL_MSG_TYPE_GET_CLIPBOARD:
            msg = await self.device_client.controller.get_clipboard()
            await self.send(bytes_data=b'\x00\x00\x00\x02\x01'+msg)
        # set_clipboard
        elif msg_type == sc_control_msg_type.SC_CONTROL_MSG_TYPE_SET_CLIPBOARD:
            sequence = await self.device_client.controller.set_clipboard(msg_data)
            await self.send(bytes_data=b'\x00\x00\x00\x02\x02'+sequence)
        # set_screen_power_mode
        elif msg_type == sc_control_msg_type.SC_CONTROL_MSG_TYPE_SET_SCREEN_POWER_MODE:
            mode = int(msg_data)
            await self.device_client.controller.set_screen_power_mode(mode)

    async def disconnect(self, code):
        self.device_client.ws_client_list.remove(self)
        if not self.device_client.ws_client_list:
            await self.device_client.stop()
