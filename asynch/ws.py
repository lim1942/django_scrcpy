import json
import struct
import asyncio
import datetime
from urllib import parse

from channels.generic.websocket import AsyncWebsocketConsumer
from asynch.client import DeviceClient


class DeviceWebsocketConsumer(AsyncWebsocketConsumer):
    WS_CLIENT_DICT = dict()
    DEVICE_CLIENT_DICT = dict()
    VIDEO_TASK_DICT = dict()
    CONTROL_TASK_DICT = dict()

    @classmethod
    async def cancel_task(cls, task):
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            print("task is cancelled now")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.query_params = None
        self.device_id = None
        self.device_client = None
        self.video_task = None
        self.control_task = None

    async def connect(self):
        await self.accept()
        self.query_params = parse.parse_qs(self.scope['query_string'].decode())
        self.device_id = self.scope['url_route']['kwargs']['device_id'].replace(',', '.').replace('_', ':')
        # 1.关闭老的device_client
        old_device_client = self.DEVICE_CLIENT_DICT.get(self.device_id, None)
        if old_device_client:
            await old_device_client.disconnect()
            del self.DEVICE_CLIENT_DICT[self.device_id]
        # 2.关闭关联的异步任务
        await self.stop_task()
        # 3.获取新的device_client
        config_dict = json.loads(self.query_params['config'][0])
        self.device_client = self.DEVICE_CLIENT_DICT[self.device_id] = DeviceClient(self.device_id, **config_dict)
        await self.device_client.connect()
        # 4.记录当前client到CLIENT_DICT
        self.add_client_record()
        # 5.开启异步video任务
        await self.start_task()

    async def receive(self, text_data=None, bytes_data=None):
        print(self.device_id, text_data, bytes_data)
        # if self.control_socket:
        #     await self.control_socket.control_socket.write(bytes_data)

    async def disconnect(self, code):
        self.del_client_record()
        # 当前无ws客户端，关闭关联的device客户端
        if not self.WS_CLIENT_DICT[self.device_id]:
            await self.device_client.disconnect()
            del self.DEVICE_CLIENT_DICT[self.device_id]

    def add_client_record(self):
        self.WS_CLIENT_DICT[self.device_id] = self.WS_CLIENT_DICT.get(self.device_id, [])
        self.WS_CLIENT_DICT[self.device_id].append(self)

    def del_client_record(self):
        self.WS_CLIENT_DICT[self.device_id].remove(self)

    async def start_task(self):
        if self.device_client.send_frame_meta:
            self.video_task = self.VIDEO_TASK_DICT[self.device_id] = asyncio.ensure_future(self._video_task2())
        else:
            self.video_task = self.VIDEO_TASK_DICT[self.device_id] = asyncio.ensure_future(self._video_task1())
        self.control_task = self.CONTROL_TASK_DICT[self.device_id] = asyncio.ensure_future(self._control_task())

    async def stop_task(self):
        old_video_task = self.VIDEO_TASK_DICT.get(self.device_id)
        if old_video_task:
            await self.cancel_task(old_video_task)
            del self.VIDEO_TASK_DICT[self.device_id]
        old_control_task = self.CONTROL_TASK_DICT.get(self.device_id)
        if old_control_task:
            await self.cancel_task(old_control_task)
            del self.CONTROL_TASK_DICT[self.device_id]

    # 内存中滞留一帧，数据推送多一帧延迟，丢包率低
    async def _video_task1(self):
        data = b''
        while True:
            # 1.读取socket种的字节流，按h264里nal组装起来
            chunk = await self.device_client.video_socket.read(0x10000)
            if chunk:
                data += chunk
            else:
                print(f"{self.device_id} :video socket已经关闭！！！")
                break
            # 2.向客户端发送当前nal数据
            while True:
                next_nal_idx = data.find(b'\x00\x00\x00\x01', 4)
                if next_nal_idx > 0:
                    current_nal_data = data[:next_nal_idx]
                    data = data[next_nal_idx:]
                    for ws_client in self.WS_CLIENT_DICT.get(self.device_id, []):
                        print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'))
                        await ws_client.send(bytes_data=current_nal_data)
                else:
                    break

    # 实时推送当前帧，丢包率高
    async def _video_task2(self):
        while True:
            # 1.读取frame_meta
            frame_meta = await self.device_client.video_socket.read(12)
            if frame_meta:
                data_length = struct.unpack('>L', frame_meta[8:])[0]
            else:
                print(f"{self.device_id} :video socket已经关闭！！！")
                break
            # 2.向客户端发送当前nal
            current_nal_data = await self.device_client.video_socket.read(data_length)
            for ws_client in self.WS_CLIENT_DICT.get(self.device_id, []):
                await ws_client.send(bytes_data=current_nal_data)

    async def _control_task(self):
        while True:
            data = await self.device_client.control_socket.read(0x1000)
            if data:
                print(f'{self.device_id} :control_socket====', data)
            else:
                print(f"{self.device_id} :control socket已经关闭！！！")
                break
