import json
from urllib import parse

from channels.generic.websocket import AsyncWebsocketConsumer
from asynch.client import DeviceClient


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
        print(self.device_id, text_data, bytes_data)
        # if self.control_socket:
        #     await self.control_socket.control_socket.write(bytes_data)

    async def disconnect(self, code):
        self.device_client.ws_client_list.remove(self)
        if not self.device_client.ws_client_list:
            await self.device_client.stop()
