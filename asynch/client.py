import os
import json
import random
import struct
import asyncio
from bitstring import BitStream

from h26x_extractor.nalutypes import SPS
from asynch.controller import Controller
from asynch.adb import AsyncAdbDevice
from asynch.serializers import format_audio_data


class DeviceClient:
    # socket超时时间,毫秒
    connect_timeout = 300

    @classmethod
    async def cancel_task(cls, task):
        # If task is already finish, this operation will return False, else return True(mean cancel operation success)
        task.cancel()
        try:
            # Wait task done, Exception inside the task will raise here
            await task
            # [task cancel operation no effect] 1.task already finished
        except asyncio.CancelledError:
            # [task cancel operation success] 2.catch task CancelledError Exception
            print("task is cancelled now")
        except Exception as e:
            # [task cancel operation no effect] 3.task already finished with a normal Exception
            print(f"task await exception {type(e)}, {e}")

    def __init__(self, ws_client):
        # scrcpy参数
        self.scrcpy_kwargs = json.loads(ws_client.query_params['config'][0])
        # devices
        self.device_id = ws_client.device_id
        self.adb_device = AsyncAdbDevice(self.device_id)
        # socket
        self.deploy_socket = None
        self.video_socket = None
        self.audio_socket = None
        self.control_socket = None
        # task
        self.deploy_task = None
        self.video_task = None
        self.audio_task = None
        # 设备型号和分辨率
        self.device_name = None
        self.resolution = None
        # 设备控制并发锁
        self.device_lock = asyncio.Lock()
        # 设备控制器
        self.controller = Controller(self)
        # 需要推流的ws_client
        self.ws_client = ws_client

    def update_resolution(self, current_nal_data):
        # when read a sps frame, change origin resolution
        if current_nal_data.startswith(b'\x00\x00\x00\x01g'):
            # sps resolution not equal device resolution, so reuse and transform original resolution
            sps = SPS(BitStream(current_nal_data[5:]), False)
            width = (sps.pic_width_in_mbs_minus_1 + 1) * 16
            height = (2 - sps.frame_mbs_only_flag) * (sps.pic_height_in_map_units_minus_1 + 1) * 16
            if width > height:
                resolution = (max(self.resolution), min(self.resolution))
            else:
                resolution = (min(self.resolution), max(self.resolution))
            self.resolution = resolution

    async def shell(self, command):
        if isinstance(command, list):
            command = ' '.join(command)
        command = command.replace('True', 'true').replace('False', 'false')
        shell_socket = await self.adb_device.create_shell_socket(command)
        return shell_socket

    async def deploy_server(self):
        # 1.推送jar包
        server_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scrcpy-server-v2.0")
        await self.adb_device.push_file(server_file_path, "/data/local/tmp/scrcpy-server.jar")
        # 2.启动一个adb socket去部署scrcpy_server
        self.scrcpy_kwargs['scid'] = '0' + ''.join([hex(random.randint(0, 15))[-1] for _ in range(7)])
        commands = [
            "CLASSPATH=/data/local/tmp/scrcpy-server.jar",
            "app_process",
            "/",
            "com.genymobile.scrcpy.Server",
            "2.0",
            *[f"{k}={v}" for k, v in self.scrcpy_kwargs.items()]
        ]
        self.deploy_socket = await self.shell(commands)

    async def create_socket(self):
        # 1.video_socket
        socket_name = 'localabstract:scrcpy_%s' % self.scrcpy_kwargs['scid']
        self.video_socket = await self.adb_device.create_connection_socket(socket_name, timeout=self.connect_timeout)
        dummy_byte = await self.video_socket.read_exactly(1)
        if not len(dummy_byte) or dummy_byte != b"\x00":
            raise ConnectionError("not receive Dummy Byte")
        # 2.audio_socket
        if self.scrcpy_kwargs['audio']:
            self.audio_socket = await self.adb_device.create_connection_socket(socket_name, timeout=self.connect_timeout)
        # 3.control_socket
        if self.scrcpy_kwargs['control']:
            self.control_socket = await self.adb_device.create_connection_socket(socket_name, timeout=self.connect_timeout)

    async def _deploy_task(self):
        while True:
            data = await self.deploy_socket.read_string_line()
            if not data:
                break
            print(f"【{self.device_id}】:", data.rstrip('\r\n').rstrip('\n'))

    async def _video_task(self):
        self.device_name = (await self.video_socket.read_exactly(64)).decode("utf-8").rstrip("\x00")
        video_info = (await self.video_socket.read_exactly(12))
        accept_video_encode = video_info[:4]
        self.resolution = struct.unpack(">LL", video_info[4:])
        if self.scrcpy_kwargs['send_frame_meta']:
            while True:
                try:
                    # 1.读取frame_meta
                    frame_meta = await self.video_socket.read_exactly(12)
                    # 用>大端解析pts(当前帧距离第一帧的微秒数)
                    # pts = struct.unpack('>Q', frame_meta[:8])[0]
                    # print(pts, pts/1000000)
                    data_length = struct.unpack('>L', frame_meta[8:])[0]
                    current_nal_data = await self.video_socket.read_exactly(data_length)
                    self.update_resolution(current_nal_data)
                    # 2.向客户端发送当前nal
                    await self.ws_client.send(bytes_data=current_nal_data)
                except (asyncio.streams.IncompleteReadError, AttributeError):
                    break
        else:
            while True:
                try:
                    data = await self.video_socket.read_until(b'\x00\x00\x00\x01')
                    current_nal_data = b'\x00\x00\x00\x01' + data.rstrip(b'\x00\x00\x00\x01')
                    self.update_resolution(current_nal_data)
                    await self.ws_client.send(bytes_data=current_nal_data)
                except (asyncio.streams.IncompleteReadError, AttributeError):
                    break

    async def _audio_task(self):
        accept_audio_encode = await self.audio_socket.read_exactly(4)
        while True:
            try:
                # 1.读取frame_meta
                frame_meta = await self.audio_socket.read_exactly(12)
                data_length = struct.unpack('>L', frame_meta[8:])[0]
                current_nal_data = await self.audio_socket.read_exactly(data_length)
                # 2.向客户端发送当前nal
                await self.ws_client.send(bytes_data=format_audio_data(current_nal_data))
            except (asyncio.streams.IncompleteReadError, AttributeError):
                break

    async def start(self):
        # deploy
        await self.deploy_server()
        self.deploy_task = asyncio.create_task(self._deploy_task())
        # video
        await self.create_socket()
        self.video_task = asyncio.create_task(self._video_task())
        # audio
        if self.scrcpy_kwargs['audio']:
            self.audio_task = asyncio.create_task(self._audio_task())

    async def stop(self):
        # video
        await self.video_socket.disconnect()
        await self.cancel_task(self.video_task)
        # audio
        if self.scrcpy_kwargs['audio']:
            await self.audio_socket.disconnect()
            await self.cancel_task(self.audio_task)
        # control
        if self.control_socket:
            await self.control_socket.disconnect()
        # deploy
        await self.deploy_socket.disconnect()
        await self.cancel_task(self.deploy_task)
