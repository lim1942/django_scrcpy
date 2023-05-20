import os
import sys
import uuid
import json
import random
import struct
import asyncio
import datetime

from channels.db import database_sync_to_async

from asynch.controller import Controller
from asynch.adb import AsyncAdbDevice
from asynch.serializers import format_audio_data
from asynch.recorder import RecorderTool
from django_scrcpy.settings import MEDIA_ROOT


class DeviceClient:
    # 录屏工具
    recorder_tool = RecorderTool
    recorder_tool.start_server()
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
        self.session_id = uuid.uuid4().hex
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
        # 录屏相关
        self.recorder_socket = None
        self.recorder_format = None
        self.recorder_start_time = None
        self.recorder_finish_time = None

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
        # 4.metadata
        self.device_name = (await self.video_socket.read_exactly(64)).decode("utf-8").rstrip("\x00")
        video_info = (await self.video_socket.read_exactly(12))
        accept_video_encode = video_info[:4]
        self.resolution = struct.unpack(">LL", video_info[4:])
        # 5.send meta to recorder
        await self.send_to_recorder(video_info)
        if self.scrcpy_kwargs['audio']:
            accept_audio_encode = await self.audio_socket.read_exactly(4)
            await self.send_to_recorder(accept_audio_encode)
        else:
            await self.send_to_recorder(struct.pack(">L", 0))

    async def _deploy_task(self):
        while True:
            data = await self.deploy_socket.read_string_line()
            if not data:
                break
            print(f"【{self.device_id}】:", data.rstrip('\r\n').rstrip('\n'))

    async def _video_task(self):
        try:
            while True:
                # 1.读取frame_meta
                frame_meta = await self.video_socket.read_exactly(12)
                data_length = struct.unpack('>L', frame_meta[8:])[0]
                current_nal_data = await self.video_socket.read_exactly(data_length)
                # 2.向客户端发送当前nal
                await self.ws_client.send(bytes_data=current_nal_data)
                await self.send_to_recorder(frame_meta+current_nal_data)
        finally:
            await self.ws_client.close()


    async def _audio_task(self):
        try:
            while True:
                # 1.读取frame_meta
                frame_meta = await self.audio_socket.read_exactly(12)
                data_length = struct.unpack('>L', frame_meta[8:])[0]
                current_nal_data = await self.audio_socket.read_exactly(data_length)
                # 2.向客户端发送当前nal
                await self.ws_client.send(bytes_data=format_audio_data(current_nal_data))
                await self.send_to_recorder(frame_meta + current_nal_data)
        finally:
            await self.ws_client.close()

    async def handle_first_config_nal(self):
        # 1.video_config_packet
        frame_meta = await self.video_socket.read_exactly(12)
        data_length = struct.unpack('>L', frame_meta[8:])[0]
        video_config_nal = await self.video_socket.read_exactly(data_length)
        await self.ws_client.send(bytes_data=video_config_nal)
        await self.send_to_recorder(frame_meta + video_config_nal)
        # 2.audio_config_packet
        if self.scrcpy_kwargs['audio']:
            frame_meta = await self.audio_socket.read_exactly(12)
            data_length = struct.unpack('>L', frame_meta[8:])[0]
            audio_config_nal = await self.audio_socket.read_exactly(data_length)
            await self.ws_client.send(bytes_data=format_audio_data(audio_config_nal))
            await self.send_to_recorder(frame_meta + audio_config_nal)

    async def start_recorder(self):
        if sys.platform.startswith('linux') and self.scrcpy_kwargs.pop('recorder', None):
            self.recorder_format = 'mkv' if self.scrcpy_kwargs.pop('recorder_mkv', None) else 'mp4'
            cmd = 'asset/recorder.out'
            args = [f'{self.session_id}.{self.recorder_format}', '127.0.0.1', '45678', 'media/video/']
            await asyncio.create_subprocess_exec(cmd, *args, stdout=sys.stdout, stderr=sys.stderr)
            for _ in range(200):
                await asyncio.sleep(0.01)
                if self.session_id in self.recorder_tool.RECORDER_CLIENT_SOCKET:
                    self.recorder_socket = self.recorder_tool.RECORDER_CLIENT_SOCKET[self.session_id]
                    print(f"{self.device_id}:{self.session_id} success get recorder_socket")
                    break

            else:
                print(f"{self.device_id}:{self.session_id} error in get recorder_socket")

    async def send_to_recorder(self, data):
        if self.recorder_socket:
            await self.recorder_socket.write(data)

    async def stop_recorder(self):
        if self.recorder_socket:
            from general.models import Video
            self.recorder_socket = None
            await self.recorder_tool.del_recorder_socket(self.session_id)
            data = dict(
                video_id=self.session_id,
                device_id=self.device_id,
                format=self.recorder_format,
                duration=(self.recorder_finish_time-self.recorder_start_time).seconds,
                size=os.path.getsize(os.path.join(MEDIA_ROOT, 'video', f"{self.session_id}.{self.recorder_format}")),
                start_time=self.recorder_start_time,
                finish_time=self.recorder_finish_time,
                config=json.dumps(self.scrcpy_kwargs)
            )
            await database_sync_to_async(Video.objects.create)(**data)

    async def start(self):
        # 1.start deploy server
        await self.deploy_server()
        self.deploy_task = asyncio.create_task(self._deploy_task())
        # 2.start_recorder
        await self.start_recorder()
        # 3.create socket and get first config nal
        await self.create_socket()
        self.recorder_start_time = datetime.datetime.now()
        await self.handle_first_config_nal()
        # 4.video task
        self.video_task = asyncio.create_task(self._video_task())
        # 5.audio task
        if self.scrcpy_kwargs['audio']:
            self.audio_task = asyncio.create_task(self._audio_task())

    async def stop(self):
        # 1.stop video task
        self.recorder_finish_time = datetime.datetime.now()
        if self.video_socket:
            await self.video_socket.disconnect()
            self.video_socket = None
        if self.video_task:
            await self.cancel_task(self.video_task)
            self.video_task = None
        # 2.stop audio task
        if self.audio_socket:
            await self.audio_socket.disconnect()
            self.audio_socket = None
        if self.audio_task:
            await self.cancel_task(self.audio_task)
            self.audio_task = None
        # 3.close control socket
        if self.control_socket:
            await self.control_socket.disconnect()
            self.control_socket = None
        # 4.stop deploy server
        if self.deploy_socket:
            await self.deploy_socket.disconnect()
            self.deploy_socket = None
        if self.deploy_task:
            await self.cancel_task(self.deploy_task)
            self.deploy_task = None
        # 5.stop_recorder
        await self.stop_recorder()
        print(f"DeviceClient:{self.device_id}: stoped !!!")