import os
import struct
import asyncio
import subprocess

from asynch.asocket import AsyncAdbSocket


class DeviceClient:
    @classmethod
    def shell(cls, command):
        """because asyncio.subprocess has bug on windows, so use normal subprocess
        这里应该使用asyncio.subprocess,因为在windows平台该模块有bug，故使用同步的subprocess
        """
        return subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

    @classmethod
    async def cancel_task(cls, task):
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            print("task is cancelled now")

    def __init__(self, device_id, max_size=720, bit_rate=8000000, max_fps=25, lock_video_orientation=-1,
                 crop='', stay_awake=True, codec_options='', encoder_name="OMX.google.h264.encoder",
                 send_frame_meta=True, connect_timeout=300):
        # scrcpy_server启动参数
        self.device_id = device_id
        self.max_size = max_size
        self.bit_rate = bit_rate
        self.max_fps = max_fps
        self.lock_video_orientation = lock_video_orientation
        self.crop = crop
        self.stay_awake = stay_awake
        self.codec_options = codec_options
        self.encoder_name = encoder_name
        self.send_frame_meta = send_frame_meta
        # adb socket连接超时时间
        self.connect_timeout = connect_timeout
        # 连接设备的socket
        self.video_socket = None
        self.control_socket = None
        # 部署进程
        self.deploy_process = None
        # 设备型号和分辨率
        self.device_name = None
        self.resolution = None
        # 设备并发锁
        self.device_lock = asyncio.Lock()
        # 需要推流得ws_client
        self.ws_client_list = list()
        # 监听设备socket的任务
        self.video_task = None
        self.control_task = None

    def update(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        print(f"update {self.device_id} to {kwargs}")

    def get_command(self, cmd_list):
        command = ' '.join(cmd_list)
        if not command.startswith('adb'):
            command = f'adb -s {self.device_id} {command}'
        return command

    async def prepare_server(self):
        # 1.推送jar包
        server_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scrcpy-server-v1.24")
        commands1 = self.get_command(['push', server_file_path, f"/data/local/tmp/scrcpy-server.jar"])
        # 2.启动server
        commands2 = self.get_command([
            "shell",
            "CLASSPATH=/data/local/tmp/scrcpy-server.jar",
            "app_process",
            "/",
            "com.genymobile.scrcpy.Server",
            "1.24",  # Scrcpy server version
            "log_level=info",  # Log level: info, verbose...
            f"max_size={self.max_size}",  # Max screen width (long side)
            f"bit_rate={self.bit_rate}",  # Bitrate of video
            f"max_fps={self.max_fps}",  # Max frame per second
            f"lock_video_orientation={self.lock_video_orientation}",    # Lock screen orientation
            "tunnel_forward=true",  # Tunnel forward
            f"crop={self.crop}",  # Crop screen
            "control=true",  # Control enabled
            "display_id=0",  # Display id
            "show_touches=false",  # Show touches
            f"stay_awake={self.stay_awake}",  # Stay awake
            f"codec_options={self.codec_options}",  # Codec (video encoding) options
            f"encoder_name={self.encoder_name}",  # Encoder name
            "power_off_on_close=false",  # Power off screen after server closed
            "clipboard_autosync=true",   # auto sync clipboard
            "raw_video_stream=false",    # video_socket just receive raw_video_stream
            f"send_frame_meta={self.send_frame_meta}",    # receive frame_mete
        ])
        self.deploy_process = self.shell(f'{commands1} && {commands2}')

    async def prepare_socket(self):
        self.video_socket = AsyncAdbSocket(self.device_id, 'localabstract:scrcpy', connect_timeout=self.connect_timeout)
        await self.video_socket.connect()
        # 1.video_socket连接成功标志
        dummy_byte = await self.video_socket.read(1)
        if not len(dummy_byte) or dummy_byte != b"\x00":
            raise ConnectionError("not receive Dummy Byte")
        # 2.连接control_socket
        self.control_socket = AsyncAdbSocket(self.device_id, 'localabstract:scrcpy', connect_timeout=self.connect_timeout)
        await self.control_socket.connect()
        # 3.获取设备类型
        self.device_name = (await self.video_socket.read(64)).decode("utf-8").rstrip("\x00")
        if not len(self.device_name):
            raise ConnectionError("not receive Device Name")
        # 4.获取分辨率
        self.resolution = struct.unpack(">HH", await self.video_socket.read(4))

    # 内存中滞留一帧，数据推送多一帧延迟，丢包率低
    async def _video_task1(self):
        data = b''
        while True:
            # 1.读取socket种的字节流，按h264里nal组装起来
            chunk = await self.video_socket.read(0x10000)
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
                    for ws_client in self.ws_client_list:
                        await ws_client.send(bytes_data=current_nal_data)
                else:
                    break

    # 实时推送当前帧，丢包率高
    async def _video_task2(self):
        while True:
            # 1.读取frame_meta
            frame_meta = await self.video_socket.read(12)
            if frame_meta:
                data_length = struct.unpack('>L', frame_meta[8:])[0]
            else:
                print(f"{self.device_id} :video socket已经关闭！！！")
                break
            # 2.向客户端发送当前nal
            current_nal_data = await self.video_socket.read(data_length)
            for ws_client in self.ws_client_list:
                await ws_client.send(bytes_data=current_nal_data)

    async def _control_task(self):
        while True:
            data = await self.control_socket.read(0x1000)
            if data:
                print(f'{self.device_id} :control_socket====', data)
            else:
                print(f"{self.device_id} :control socket已经关闭！！！")
                break

    async def start(self):
        await self.prepare_server()
        await self.prepare_socket()
        if self.send_frame_meta:
            self.video_task = asyncio.ensure_future(self._video_task2())
        else:
            self.video_task = asyncio.ensure_future(self._video_task1())
        self.control_task = asyncio.ensure_future(self._control_task())

    async def stop(self):
        if self.video_socket:
            await self.video_socket.disconnect()
            self.video_socket = None
        if self.control_socket:
            await self.control_socket.disconnect()
            self.control_socket = None
        if self.deploy_process:
            self.shell(self.get_command(["shell", "\"ps -ef | grep scrcpy |awk '{print $2}' |xargs kill -9\""])).wait()
            self.deploy_process.wait()
            self.deploy_process = None
        if self.video_task:
            await self.cancel_task(self.video_task)
        if self.control_task:
            await self.cancel_task(self.control_task)
