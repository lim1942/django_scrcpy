import os
import logging
import subprocess

logging.basicConfig(format='%(asctime)s:%(filename)s/%(lineno)s:%(name)s:%(threadName)s:%(levelname)s:%(message)s', level=logging.INFO)


class ScrcpyClient:
    WebSocketHandle = None

    def __init__(self, device_id, max_size=800, bit_rate=8000000, max_fps=25, lock_video_orientation=-1,
                 stay_awake=True, encoder_name="OMX.google.h264.encoder", send_frame_meta=True, connection_timeout=30):
        self.device_id = device_id
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

    def shell(self, command):
        if isinstance(command, list):
            command = ' '.join(command)
        command = f'adb -s {self.device_id} {command}'
        return subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

    def deploy_server(self):
        # 1.推送jar包到设备
        jar_name = "scrcpy-server-v1.24"
        server_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), jar_name)
        p = self.shell(['push', server_file_path, f"/data/local/tmp/scrcpy-server.jar"])
        stdout, stderr = p.communicate()
        print(stdout)
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
        p = self.shell(commands)
        # 3.等待server部署成功
        p.wait()



c= ScrcpyClient('OROZ7LZ5PJY5ZTI7')
c.deploy_server()