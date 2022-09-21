import datetime
import struct
import asyncio

from channels.generic.websocket import AsyncWebsocketConsumer
from asynch.asyncso import DeviceAsyncSocket


class VideoWebsocketConsumer(AsyncWebsocketConsumer):
    CLIENT_DICT = dict()
    VIDEO_TASK_DICT = dict()
    VIDEO_SOCKET_DICT = dict()
    CONTROL_TASK_DICT = dict()
    CONTROL_SOCKET_DICT = dict()

    @classmethod
    async def cancel_task(cls, task):
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            print("task is cancelled now")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.device_id = None
        self.video_task = None
        self.video_socket = None
        self.control_task = None
        self.control_socket = None
        self.device_name = None
        self.resolution = None

    async def connect(self):
        await self.accept()
        self.device_id = self.scope['url_route']['kwargs']['device_id']
        self.video_task = self.VIDEO_TASK_DICT.get(self.device_id, None)
        self.video_socket = self.VIDEO_SOCKET_DICT.get(self.device_id, None)
        self.control_task = self.CONTROL_TASK_DICT.get(self.device_id, None)
        self.control_socket = self.CONTROL_SOCKET_DICT.get(self.device_id, None)
        # 2.关闭当前client相关设备socket
        await self.close_socket()
        # 3.开启当前client相关设备socket
        await self.open_socket()
        # 4.关闭异步任务
        await self.stop_task()
        # 1.记录当前client到CLIENT_DICT
        self.add_client_record()
        # 5.开启异步video任务
        await self.start_task()

    async def receive(self, text_data=None, bytes_data=None):
        print(text_data, bytes_data)
        # if self.control_socket:
        #     await self.control_socket.control_socket.write(bytes_data)

    async def disconnect(self, code):
        self.del_client_record()

    def add_client_record(self):
        self.CLIENT_DICT[self.device_id] = self.CLIENT_DICT.get(self.device_id, [])
        self.CLIENT_DICT[self.device_id].append(self)

    def del_client_record(self):
        self.CLIENT_DICT[self.device_id].remove(self)

    async def open_socket(self):
        self.video_socket = self.VIDEO_SOCKET_DICT[self.device_id] = DeviceAsyncSocket(self.device_id)
        await self.VIDEO_SOCKET_DICT[self.device_id].connect()
        self.control_socket = self.CONTROL_SOCKET_DICT[self.device_id] = DeviceAsyncSocket(self.device_id)
        await self.CONTROL_SOCKET_DICT[self.device_id].connect()

    async def close_socket(self):
        if self.video_socket:
            await self.video_socket.close()
            self.video_socket = self.VIDEO_SOCKET_DICT[self.device_id] = None
        if self.control_socket:
            await self.control_socket.close()
            self.control_socket = self.CONTROL_SOCKET_DICT[self.device_id] = None

    async def stop_task(self):
        if self.video_task:
            await self.cancel_task(self.video_task)
            self.video_task = self.VIDEO_TASK_DICT[self.device_id] = None
        if self.control_task:
            await self.cancel_task(self.control_task)
            self.control_task = self.CONTROL_TASK_DICT[self.device_id] = None

    async def start_task(self):
        self.video_task = self.VIDEO_TASK_DICT[self.device_id] = asyncio.ensure_future(self._video_task2())
        self.control_task = self.CONTROL_TASK_DICT[self.device_id] = asyncio.ensure_future(self._control_task())

    # 内存中滞留一帧，数据推送多一帧延迟，丢包率低
    async def _video_task1(self):
        if not self.video_socket:
            return
        # 1.video_socket连接标志
        dummy_byte = await self.video_socket.read(1)
        if not len(dummy_byte) or dummy_byte != b"\x00":
            raise ConnectionError("not receive Dummy Byte")
        # 2.获取设备名
        self.device_name = (await self.video_socket.read(64)).decode("utf-8").rstrip("\x00")
        if not len(self.device_name):
            raise ConnectionError("not receive Device Name")
        # 3.获取分辨率
        self.resolution = struct.unpack(">HH", await self.video_socket.read(4))
        data = b''
        while True:
            # 1.读取socket种的字节流，按h264里nal组装起来
            chunk = await self.video_socket.read(0x10000)
            if chunk:
                data += chunk
            else:
                print("video socket已经关闭！！！")
                break
            # 2.向客户端发送当前nal数据
            while True:
                next_nal_idx = data.find(b'\x00\x00\x00\x01', 4)
                if next_nal_idx > 0:
                    current_nal_data = data[:next_nal_idx]
                    data = data[next_nal_idx:]
                    for client in self.CLIENT_DICT.get(self.device_id, []):
                        print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'))
                        await client.send(bytes_data=current_nal_data)
                else:
                    break

    # 实时推送当前帧，丢包率高
    async def _video_task2(self):
        if not self.video_socket:
            return
        # 1.video_socket连接标志
        dummy_byte = await self.video_socket.read(1)
        if not len(dummy_byte) or dummy_byte != b"\x00":
            raise ConnectionError("not receive Dummy Byte")
        # 2.获取设备名
        self.device_name = (await self.video_socket.read(64)).decode("utf-8").rstrip("\x00")
        if not len(self.device_name):
            raise ConnectionError("not receive Device Name")
        # 3.获取分辨率
        self.resolution = struct.unpack(">HH", await self.video_socket.read(4))
        while True:
            # 1.读取frame_meta
            frame_meta = await self.video_socket.read(12)
            if frame_meta:
                data_length = struct.unpack('>L', frame_meta[8:])[0]
            else:
                print("video socket已经关闭！！！")
                break
            # 2.向客户端发送当前nal
            current_nal_data = await self.video_socket.read(data_length)
            for client in self.CLIENT_DICT.get(self.device_id, []):
                await client.send(bytes_data=current_nal_data)

    async def _control_task(self):
        if not self.control_socket:
            return
        while True:
            data = await self.control_socket.read(0x1000)
            if data:
                print(data)
            else:
                print("control socket已经关闭！！！")
                break
