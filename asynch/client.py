import os
import struct
import asyncio
import subprocess

from django_scrcpy.settings import ADB_SERVER_ADDR, ADB_SERVER_PORT


class AsyncSocket:
    @classmethod
    def cmd_format(cls, cmd):
        return "{:04x}{}".format(len(cmd), cmd).encode("utf-8")

    def __init__(self, device_id, timeout=10):
        self.device_id = device_id
        self.timeout = timeout
        self.reader = None
        self.writer = None

    async def connect(self):
        self.reader, self.writer = await asyncio.wait_for(asyncio.open_connection(ADB_SERVER_ADDR, ADB_SERVER_PORT), 2)
        self.writer.write(self.cmd_format(f'host:transport:{self.device_id}'))
        await self.writer.drain()
        assert await self.reader.read(4) == b'OKAY'
        await asyncio.sleep(1)
        self.writer.write(self.cmd_format('localabstract:scrcpy'))
        await self.writer.drain()
        assert await self.reader.read(4) == b'OKAY'

    async def read(self, cnt=-1):
        return await self.reader.read(cnt)

    async def write(self, data):
        self.writer.write(data)
        await self.writer.drain()

    async def disconnect(self):
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
            self.writer = self.reader = None


class DeviceClient:
    def __init__(self, device_id, max_size=800, bit_rate=8000000, max_fps=25, lock_video_orientation=-1,
                 crop='', stay_awake=True, codec_options='', encoder_name="OMX.google.h264.encoder",
                 send_frame_meta=True, socket_timeout=30):
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
        # socket 连接超时时间
        self.socket_timeout = socket_timeout
        # 连接到设备的socket和部署进程
        self.video_socket = None
        self.control_socket = None
        self.deploy_process = None
        # 当前client是否存活
        self.alive = False
        # 设备型号和分辨率
        self.device_name = None
        self.resolution = None

    def shell(self, command):
        """because asyncio.subprocess has bug on windows, so use normal subprocess
        这里应该使用asyncio.subprocess,因为在windows平台该模块有bug，故使用同步的subprocess
        """
        if isinstance(command, list):
            command = ' '.join(command)
        command = f'adb -s {self.device_id} {command}'
        return subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

    async def prepare_server(self):
        # 1.推送jar包到设备
        jar_name = "scrcpy-server-v1.24"
        server_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), jar_name)
        self.shell(['push', server_file_path, f"/data/local/tmp/scrcpy-server.jar"])
        # 2.启动server
        commands = [
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
            f"lock_video_orientation={self.lock_video_orientation}",    # Lock screen orientation: LOCK_SCREEN_ORIENTATION
            "tunnel_forward=true",  # Tunnel forward
            f"crop={self.crop}",  # Crop screen
            "control=true",  # Control enabled
            "display_id=0",  # Display id
            "show_touches=false",  # Show touches
            f"stay_awake={self.stay_awake}",  # Stay awake
            f"codec_options={self.codec_options}",  # Codec (video encoding) options
            f"encoder_name={self.encoder_name}",  # Encoder name
            "power_off_on_close=false",  # Power off screen after server closed
            "raw_video_stream=false",    # video_socket just receive raw_video_stream
            f"send_frame_meta={self.send_frame_meta}",    # receive frame_mete
        ]
        self.deploy_process = self.shell(commands)

    async def prepare_socket(self):
        self.video_socket = AsyncSocket(self.device_id, timeout=self.socket_timeout)
        await self.video_socket.connect()
        # 1.video_socket连接成功标志
        dummy_byte = await self.video_socket.read(1)
        if not len(dummy_byte) or dummy_byte != b"\x00":
            raise ConnectionError("not receive Dummy Byte")
        # 2.连接control_socket
        self.control_socket = AsyncSocket(self.device_id, timeout=self.socket_timeout)
        await self.control_socket.connect()
        # 3.获取设备类型
        self.device_name = (await self.video_socket.read(64)).decode("utf-8").rstrip("\x00")
        if not len(self.device_name):
            raise ConnectionError("not receive Device Name")
        # 4.获取分辨率
        self.resolution = struct.unpack(">HH", await self.video_socket.read(4))

    async def connect(self):
        await self.prepare_server()
        await self.prepare_socket()
        self.alive = True

    async def disconnect(self):
        self.alive = False
        if self.video_socket:
            await self.video_socket.disconnect()
            self.video_socket = None
        if self.control_socket:
            await self.control_socket.disconnect()
            self.control_socket = None
        # if self.deploy_process:
        #     # todo 不能关闭手机上的scrcpy，等待scrcpy自己关闭
        #     self.deploy_process.terminate()
        #     self.deploy_process = None
