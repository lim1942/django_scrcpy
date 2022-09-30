import os
import struct
import asyncio
from bitstring import BitStream

from h26x_extractor.nalutypes import SPS
from asynch.controller import Controller
from asynch.adb import AsyncAdbDevice


class DeviceClient:
    def __init__(self, device_id,
                 log_level='verbose',
                 max_size=720,
                 bit_rate=800000,
                 max_fps=25,
                 lock_video_orientation=-1,
                 crop='',
                 control=True,
                 display_id=0,
                 show_touches=False,
                 stay_awake=True,
                 codec_options="profile=1,level=2",
                 encoder_name="OMX.google.h264.encoder",
                 power_off_on_close=False,
                 downsize_on_error=True,
                 power_on=True,
                 send_frame_meta=True,
                 connect_timeout=300,
                 deploy_shell_log=True):
        self.device_id = device_id
        self.adb_device = AsyncAdbDevice(self.device_id)
        # scrcpy_server启动参数
        self.log_level = log_level
        self.max_size = max_size
        self.bit_rate = bit_rate
        self.max_fps = max_fps
        self.lock_video_orientation = lock_video_orientation
        self.crop = crop
        self.control = control
        self.display_id = display_id
        self.show_touches = show_touches
        self.stay_awake = stay_awake
        self.codec_options = codec_options
        self.encoder_name = encoder_name
        self.power_off_on_close = power_off_on_close
        self.downsize_on_error = downsize_on_error
        self.power_on = power_on
        self.send_frame_meta = send_frame_meta
        # adb socket连接超时时间
        self.connect_timeout = connect_timeout
        # 是否获取scrcpy server的日志, 部署scrcpy_server的socket和task
        self.deploy_shell_log = deploy_shell_log
        self.deploy_shell_socket = None
        self.deploy_shell_task = None
        # 连接设备的socket, 监听设备socket的video_task任务
        self.video_socket = None
        self.control_socket = None
        self.video_task = None
        # 设备型号和分辨率
        self.device_name = None
        self.resolution = None
        # 设备并发锁
        self.device_lock = asyncio.Lock()
        # 设备控制器
        self.controller = Controller(self)
        # 需要推流得ws_client
        self.ws_client_list = list()

    def update(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

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
        server_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scrcpy-server-v1.24")
        await self.adb_device.push_file(server_file_path, "/data/local/tmp/scrcpy-server.jar")
        # 2.启动一个adb socket去部署scrcpy_server
        commands2 = [
            "CLASSPATH=/data/local/tmp/scrcpy-server.jar",
            "app_process",
            "/",
            "com.genymobile.scrcpy.Server",
            "1.24",  # Scrcpy server version
            f"log_level={self.log_level}",  # Log level: info, verbose...
            f"max_size={self.max_size}",  # Max screen width (long side)
            f"bit_rate={self.bit_rate}",  # Bitrate of video
            f"max_fps={self.max_fps}",  # Max frame per second
            f"lock_video_orientation={self.lock_video_orientation}",    # Lock screen orientation
            "tunnel_forward=true",  # Tunnel forward
            f"crop={self.crop}",  # Crop screen
            f"control={self.control}",  # Control enabled
            f"display_id={self.display_id}",  # Display id
            f"show_touches={self.show_touches}",  # Show touches
            f"stay_awake={self.stay_awake}",  # scrcpy server Stay awake
            f"codec_options={self.codec_options}",  # Codec (video encoding) options
            f"encoder_name={self.encoder_name}",  # Encoder name
            f"power_off_on_close={self.power_off_on_close}",  # Power off screen after server closed
            "clipboard_autosync=false",  # auto sync clipboard
            f"downsize_on_error={self.downsize_on_error}",   # when encode screen error downsize and retry encode screen
            "cleanup=true",     # enable cleanup thread
            f"power_on={self.power_on}",   # power on when scrcpy deploy
            "send_device_meta=true",    # send device name, device resolution when video socket connect
            f"send_frame_meta={self.send_frame_meta}",    # receive frame_mete,
            "send_dummy_byte=true",     # send dummy byte when video socket connect
            "raw_video_stream=false",  # video_socket just receive raw_video_stream
        ]
        self.deploy_shell_socket = await self.shell(commands2)
        if self.deploy_shell_log:
            self.deploy_shell_task = asyncio.ensure_future(self._srccpy_server_task())

    async def prepare_socket(self):
        # 1.video_socket
        self.video_socket = await self.adb_device.create_connection_socket('localabstract:scrcpy', timeout=self.connect_timeout)
        dummy_byte = await self.video_socket.read_exactly(1)
        if not len(dummy_byte) or dummy_byte != b"\x00":
            raise ConnectionError("not receive Dummy Byte")
        # 2.control_socket
        if self.control:
            self.control_socket = await self.adb_device.create_connection_socket('localabstract:scrcpy', timeout=self.connect_timeout)
        # 3.device information
        self.device_name = (await self.video_socket.read_exactly(64)).decode("utf-8").rstrip("\x00")
        if not len(self.device_name):
            raise ConnectionError("not receive Device Name")
        self.resolution = struct.unpack(">HH", await self.video_socket.read_exactly(4))

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
            except asyncio.streams.IncompleteReadError:
                break

    # 实时推送当前帧，可能丢包
    async def _video_task2(self):
        while True:
            try:
                # 1.读取frame_meta
                frame_meta = await self.video_socket.read_exactly(12)
                data_length = struct.unpack('>L', frame_meta[8:])[0]
                current_nal_data = await self.video_socket.read_exactly(data_length)
                self.update_resolution(current_nal_data)
                # 2.向客户端发送当前nal
                for ws_client in self.ws_client_list:
                    await ws_client.send(bytes_data=current_nal_data)
            except asyncio.streams.IncompleteReadError:
                break

    async def start(self):
        await self.prepare_server()
        await self.prepare_socket()
        if self.send_frame_meta:
            self.video_task = asyncio.ensure_future(self._video_task2())
        else:
            self.video_task = asyncio.ensure_future(self._video_task1())

    async def stop(self):
        if self.video_socket:
            await self.video_socket.disconnect()
            self.video_socket = None
            self.video_task = None
        if self.control_socket:
            await self.control_socket.disconnect()
            self.control_socket = None
        if self.deploy_shell_socket:
            await self.deploy_shell_socket.disconnect()
            self.deploy_shell_socket = None
            self.deploy_shell_task = None
