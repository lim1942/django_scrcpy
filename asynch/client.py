import os
import random
import struct
import asyncio
from bitstring import BitStream

from h26x_extractor.nalutypes import SPS
from asynch.controller import Controller
from asynch.adb import AsyncAdbDevice


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

    def __init__(self, device_id, scrcpy_kwargs):
        # scrcpy参数
        self.scrcpy_kwargs = scrcpy_kwargs
        # devices
        self.device_id = device_id
        self.adb_device = AsyncAdbDevice(self.device_id)
        # socket
        self.deploy_shell_socket = None
        self.video_socket = None
        self.audio_socket = None
        self.control_socket = None
        # task
        self.deploy_shell_task = None
        self.video_task = None
        self.audio_task = None
        # 设备型号和分辨率
        self.device_name = None
        self.resolution = None
        # 设备并发锁
        self.device_lock = asyncio.Lock()
        # 设备控制器
        self.controller = Controller(self)
        # 需要推流得ws_client
        self.ws_client_list = list()

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

    async def prepare_server(self):
        # 1.推送jar包
        server_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scrcpy-server-v2.0")
        await self.adb_device.push_file(server_file_path, "/data/local/tmp/scrcpy-server.jar")
        # 2.启动一个adb socket去部署scrcpy_server
        self.scrcpy_kwargs['scid'] = '0' + ''.join([hex(random.randint(0, 15))[-1] for _ in range(7)])
        commands2 = [
            "CLASSPATH=/data/local/tmp/scrcpy-server.jar",
            "app_process",
            "/",
            "com.genymobile.scrcpy.Server",
            "2.0",
        ]
        commands2.extend([f"{k}={v}" for k, v in self.scrcpy_kwargs.items()])
        self.deploy_shell_socket = await self.shell(commands2)

    async def prepare_socket(self):
        # 1.video_socket
        socket_name = 'localabstract:scrcpy_%s' % self.scrcpy_kwargs['scid']
        self.video_socket = await self.adb_device.create_connection_socket(socket_name, timeout=self.connect_timeout)
        dummy_byte = await self.video_socket.read_exactly(1)
        if not len(dummy_byte) or dummy_byte != b"\x00":
            raise ConnectionError("not receive Dummy Byte")
        # 2.control_socket
        self.audio_socket = await self.adb_device.create_connection_socket(socket_name, timeout=self.connect_timeout)
        self.control_socket = await self.adb_device.create_connection_socket(socket_name, timeout=self.connect_timeout)
        # 3.device information
        self.device_name = (await self.video_socket.read_exactly(64)).decode("utf-8").rstrip("\x00")
        video_info = (await self.video_socket.read_exactly(12))
        encode_name = video_info[:4]
        self.resolution = struct.unpack(">LL", video_info[4:])
        print(encode_name, self.resolution)

    async def _srccpy_server_task(self):
        while True:
            data = await self.deploy_shell_socket.read_string_line()
            if not data:
                break
            print(f"【{self.device_id}】:", data.rstrip('\r\n').rstrip('\n'))

    # 滞留一帧，数据推送多一帧延迟，丢包率低
    async def _video_task1(self):
        while True:
            try:
                data = await self.video_socket.read_until(b'\x00\x00\x00\x01')
                current_nal_data = b'\x00\x00\x00\x01' + data.rstrip(b'\x00\x00\x00\x01')
                self.update_resolution(current_nal_data)
                for ws_client in self.ws_client_list:
                    await ws_client.send(bytes_data=current_nal_data)
            except (asyncio.streams.IncompleteReadError, AttributeError):
                break

    # 实时推送当前帧，可能丢包
    async def _video_task2(self):
        frame_cnt = 0
        while True:
            try:
                # 1.读取frame_meta
                frame_meta = await self.video_socket.read_exactly(12)
                # 用>大端解析pts(当前帧距离第一帧的微秒数)
                # frame_cnt += 1
                # pts = struct.unpack('>Q', frame_meta[:8])[0]
                # print(pts, pts/1000000, frame_cnt)
                data_length = struct.unpack('>L', frame_meta[8:])[0]
                current_nal_data = await self.video_socket.read_exactly(data_length)
                self.update_resolution(current_nal_data)
                # 2.向客户端发送当前nal
                for ws_client in self.ws_client_list:
                    await ws_client.send(bytes_data=current_nal_data)
            except (asyncio.streams.IncompleteReadError, AttributeError):
                break

    async def start(self):
        await self.prepare_server()
        self.deploy_shell_task = asyncio.create_task(self._srccpy_server_task())
        await self.prepare_socket()
        if self.scrcpy_kwargs['send_frame_meta']:
            self.video_task = asyncio.create_task(self._video_task2())
        else:
            self.video_task = asyncio.create_task(self._video_task1())

    async def stop(self):
        if self.video_socket:
            await self.video_socket.disconnect()
            self.video_socket = None
        if self.video_task:
            await self.cancel_task(self.video_task)
            self.video_task = None
        if self.control_socket:
            await self.control_socket.disconnect()
            self.control_socket = None
        if self.deploy_shell_socket:
            await self.deploy_shell_socket.disconnect()
            self.deploy_shell_socket = None
        if self.deploy_shell_task:
            await self.cancel_task(self.deploy_shell_task)
            self.deploy_shell_task = None
