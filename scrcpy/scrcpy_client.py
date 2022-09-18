import os
import time
import struct
import logging
import threading
from adbutils import AdbError, Network, adb
from scrcpy.control import ControlSender
logging.basicConfig(format='%(asctime)s:%(filename)s/%(lineno)s:%(name)s:%(threadName)s:%(levelname)s:%(message)s', level=logging.INFO)


class ScrcpyClient:
    WebSocketHandle = None

    def __init__(self, device, max_size=800, bit_rate=8000000, max_fps=25, lock_video_orientation=-1,
                 stay_awake=True, encoder_name="OMX.google.h264.encoder", send_frame_meta=False, connection_timeout=30):
        self.device = adb.device(serial=device)
        self.max_size = max_size
        self.bit_rate = bit_rate
        self.max_fps = max_fps
        self.lock_video_orientation = lock_video_orientation
        self.encoder_name = encoder_name
        self.stay_awake = stay_awake
        self.send_frame_meta = send_frame_meta
        # client链接server超时时间，单位毫秒
        self.connection_timeout = connection_timeout
        # 当前client是否存活
        self.alive = False
        # 部署server的shell
        self.server_shell = None
        # 视频传输的socket
        self.video_socket = None
        # 控制设备的socket，控制对象，线程锁
        self.control_socket = None
        self.control = ControlSender(self)
        self.control_socket_lock = threading.Lock()
        # 设备名
        self.device_name = None
        # 分辨率
        self.resolution = None
        # 绑定到websocket处理类
        self.WebSocketHandle.SCRCPY_CLIENT = self

    def deploy_server(self):
        # 1.推送jar包到设备
        jar_name = "scrcpy-server-v1.24"
        server_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), jar_name)
        self.device.sync.push(server_file_path, f"/data/local/tmp/scrcpy-server.jar")
        # 2.启动server
        commands = [
            "CLASSPATH=/data/local/tmp/scrcpy-server.jar",
            "app_process",
            "/",
            "com.genymobile.scrcpy.Server",
            "1.24",  # Scrcpy server version
            "log_level=info",  # Log level: info, verbose...
            f"max_size={self.max_size}",  # Max screen width (long side)
            f"bit_rate={self.bit_rate}",  # Bitrate of video
            f"max_fps={self.max_fps}",  # Max frame per second
            f"lock_video_orientation={self.lock_video_orientation}",# Lock screen orientation: LOCK_SCREEN_ORIENTATION
            "tunnel_forward=true",  # Tunnel forward
            # "crop=-",  # Crop screen
            "control=true",  # Control enabled
            "display_id=0",  # Display id
            "show_touches=false",  # Show touches
            f"stay_awake={self.stay_awake}",  # Stay awake
            # "codec_options=-",  # Codec (video encoding) options
            f"encoder_name={self.encoder_name}",  # Encoder name
            "power_off_on_close=false",  # Power off screen after server closed
            "raw_video_stream=false",    # video_socket just receive raw_video_stream
            f"send_frame_meta={self.send_frame_meta}",    # receive frame_mete
        ]
        self.server_shell = self.device.shell(commands, stream=True,)
        # 3.等待server部署成功
        logging.info(f"【scrcpy_server启动成功】 {self.server_shell.read(10)}")

    def connect_server(self):
        # 1.连接获取video_socket
        for _ in range(self.connection_timeout):
            try:
                self.video_socket = self.device.create_connection(Network.LOCAL_ABSTRACT, "scrcpy")
                break
            except AdbError:
                time.sleep(0.1)
                pass
        else:
            raise ConnectionError("Failed to connect scrcpy-server after 3 seconds")
        # 2.判断video_socket是否连接正常
        dummy_byte = self.video_socket.recv(100)
        if not len(dummy_byte) or dummy_byte != b"\x00":
            raise ConnectionError("Did not receive Dummy Byte!")
        # 3.连接获取control_socket
        self.control_socket = self.device.create_connection(
            Network.LOCAL_ABSTRACT, "scrcpy"
        )
        # 4.通过video_socket获取设备信息
        # 4.1 读取设备名
        self.device_name = self.video_socket.recv(64).decode("utf-8").rstrip("\x00")
        if not len(self.device_name):
            raise ConnectionError("Did not receive Device Name!")
        # 4.2 读取视频分辨率
        self.resolution = struct.unpack(">HH", self.video_socket.recv(4))
        logging.info(f"【scrcpy_client连接成功】 当前手机为【{self.device_name}】, video分辨率为{self.resolution}")

    def video_socket_recv(self, cnt):
        data = b''
        for _ in range(10):
            data_length = len(data)
            if data_length == cnt:
                return data
            data += self.video_socket.recv(cnt-data_length)
        else:
            logging.error(f"video_socket_recv 错误，data_length【{len(data)}】!= cnt【{cnt}】")

    def video_socket_handle1(self):
        while True:
            frame_meta = self.video_socket_recv(12)
            # pts为当前帧和第一帧图像间的时间间隔(纳秒),
            # pts为9开头的超大负数(1L << 63)，表示该帧为非媒体数据，
            # pts为4开头的超大正数，说明当前帧为关键帧，这个超大数与(1L << 62)按位异或可得到当前关键帧的pts
            # pts = struct.unpack('>q', frame_meta[:8])
            # 下一帧的长度
            data_length = struct.unpack('>L', frame_meta[8:])[0]
            data = self.video_socket_recv(data_length)
            for ws_client in self.WebSocketHandle.WS_CLIENTS:
                ws_client.sendMessage(data)

    def video_socket_handle2(self):
        data = b''
        while True:
            # 1.读取socket种的字节流，按h264里nal组装起来
            data += self.video_socket.recv(0x100000)
            # 2.向客户端发送当前nal数据
            while True:
                next_nal_idx = data.find(b'\x00\x00\x00\x01', 4)
                if next_nal_idx > 0:
                    current_nal_data = data[:next_nal_idx]
                    data = data[next_nal_idx:]
                    for ws_client in self.WebSocketHandle.WS_CLIENTS:
                        ws_client.sendMessage(current_nal_data)
                else:
                    break

    def run(self):
        self.deploy_server()
        self.connect_server()
        self.alive = True
        if self.send_frame_meta:
            self.video_socket_handle1()
        else:
            self.video_socket_handle2()

    def stop(self):
        self.alive = False
        if self.server_shell is not None:
            self.server_shell.close()
        if self.control_socket is not None:
            self.control_socket.close()
        if self.video_socket is not None:
            self.video_socket.close()

    @classmethod
    def run_forever(cls, device='348cb8360521'):
        scrcpy_client = cls(device)
        while True:
            try:
                scrcpy_client.run()
            except ConnectionAbortedError:
                pass
            except Exception as e:
                logging.exception(e)
            try:
                scrcpy_client.stop()
            except:
                pass

    def __del__(self):
        self.stop()


if __name__ == "__main__":
    ScrcpyClient.run_forever()
