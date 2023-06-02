import os
import re
import sys
import json
import random
import struct
import logging
import asyncio
import datetime
import threading

from asynch.tools.utils import AsyncSocket
from asynch.tools.adb import AsyncAdbDevice
from asynch.serializers import format_audio_data
from django_scrcpy.settings import MEDIA_ROOT, BASE_DIR
from asynch.constants import sc_control_msg_type, sc_copy_key, sc_screen_power_mode
from asynch.constants.input import android_metastate, android_keyevent_action, android_motionevent_action, \
    android_motionevent_buttons
logging.basicConfig(level=logging.INFO)


class DeviceRecorder:
    SERVER_PORT = 45678
    SERVER_HOST = '0.0.0.0'
    RECORDER_CLIENT_SOCKET = {}
    EVENT_LOOP = asyncio.new_event_loop()

    @classmethod
    async def accept(cls, reader, writer):
        recorder_client = AsyncSocket(reader=reader, writer=writer)
        session_id = await recorder_client.read_string_exactly(32)
        cls.RECORDER_CLIENT_SOCKET[session_id] = recorder_client
        logging.info(f"【RecorderServer】 =======> accept client {session_id}")

    @classmethod
    async def _start_server(cls):
        server = await asyncio.start_server(cls.accept, cls.SERVER_HOST, cls.SERVER_PORT)
        async with server:
            await server.serve_forever()

    @classmethod
    def start_server(cls):
        def task():
            asyncio.set_event_loop(cls.EVENT_LOOP)
            asyncio.run(cls._start_server())
        thread = threading.Thread(target=task, )
        thread.start()
        logging.info(f"【RecorderServer】 =======> start on {cls.SERVER_HOST}:{cls.SERVER_PORT}")

    @classmethod
    def get_recorder_socket(cls, session_id):
        return cls.RECORDER_CLIENT_SOCKET[session_id]

    @classmethod
    async def del_recorder_socket(cls, session_id):
        cls.RECORDER_CLIENT_SOCKET[session_id].writer.write_eof()
        await cls.RECORDER_CLIENT_SOCKET[session_id].writer.drain()
        del cls.RECORDER_CLIENT_SOCKET[session_id]
        logging.info(f"【RecorderServer】 =======> remove client {session_id}")


class DeviceController:
    def __init__(self, device_client):
        self.device = device_client

    async def empty_control_socket(self, interval=0.02, loop=10):
        for idx in range(loop):
            try:
                await asyncio.wait_for(self.device.control_socket.read(0x10000), timeout=interval)
            except:
                return

    async def inject(self, msg):
        async with self.device.device_lock:
            await self.device.control_socket.write(msg)

    async def inject_without_lock(self, msg):
        await self.device.control_socket.write(msg)

    async def inject_keycode(self, keycode, action=android_keyevent_action.AKEY_EVENT_ACTION_DOWN, repeat=0,
                       metastate=android_metastate.AMETA_NONE):
        """
        keycode: in constants.keycodes.py
        action: android_keyevent_action
        metastate: android_metastate
        inject_data: lens 14
        """
        msg_type = sc_control_msg_type.SC_CONTROL_MSG_TYPE_INJECT_KEYCODE
        inject_data = struct.pack(">BBiii", msg_type, action, keycode, repeat, metastate)
        await self.inject(inject_data)
        return inject_data

    async def inject_text(self, text):
        """
        inject_data: lens 5 + *
        """
        msg_type = sc_control_msg_type.SC_CONTROL_MSG_TYPE_INJECT_TEXT
        buffer = text.encode("utf-8")
        inject_data = struct.pack(">BI", msg_type, len(buffer)) + buffer
        await self.inject(inject_data)
        return inject_data

    async def inject_touch_event(self, x, y, resolution, action=android_motionevent_action.AMOTION_EVENT_ACTION_DOWN, touch_id=-1,
                                 pressure=1, buttons=android_motionevent_buttons.AMOTION_EVENT_BUTTON_PRIMARY):
        """
        action: android_motionevent_action
        touch_id: touch_id use to distinguish multi touch
        x: touch location x
        y: touch location y
        height: resolution height
        width: resolution width
        pressure: touch pressure. 0 or 1,1 is max
        action_button: android_motionevent_buttons, mouse key
        buttons: same as pressure 0 or 1
        inject_data: lens 32
        """
        if action == android_motionevent_action.AMOTION_EVENT_ACTION_UP:
            pressure = 0
        msg_type = sc_control_msg_type.SC_CONTROL_MSG_TYPE_INJECT_TOUCH_EVENT
        x, y = max(x, 0), max(y, 0)
        inject_data = struct.pack(">BBqiiHHHii", msg_type, action, touch_id, int(x), int(y),
                                  int(resolution[0]), int(resolution[1]), pressure, buttons, pressure)
        await self.inject(inject_data)
        return inject_data

    async def inject_scroll_event(self, x, y, distance_x, distance_y, resolution, buttons=android_motionevent_buttons.AMOTION_EVENT_BUTTON_PRIMARY):
        """
        buttons: android_motionevent_buttons
        inject_data: lens 21
        """
        msg_type = sc_control_msg_type.SC_CONTROL_MSG_TYPE_INJECT_SCROLL_EVENT
        x, y = max(x, 0), max(y, 0)
        inject_data = struct.pack(">BiiHHhhi", msg_type, int(x), int(y), int(resolution[0]),
                                  int(resolution[1]), int(distance_x)*6000, int(distance_y)*6000, buttons)
        await self.inject(inject_data)
        return inject_data

    async def back_or_screen_on(self, action=android_keyevent_action.AKEY_EVENT_ACTION_DOWN):
        """
        inject_data: lens 2
        """
        msg_type = sc_control_msg_type.SC_CONTROL_MSG_TYPE_BACK_OR_SCREEN_ON
        inject_data = struct.pack(">BB", msg_type, action)
        await self.inject(inject_data)
        return inject_data

    async def get_clipboard(self, copy_key=sc_copy_key.SC_COPY_KEY_COPY):
        """
        copy_key: none, copy, cut
        inject_data: lens 2
        """
        msg_type = sc_control_msg_type.SC_CONTROL_MSG_TYPE_GET_CLIPBOARD
        inject_data = struct.pack(">BB", msg_type, copy_key)
        async with self.device.device_lock:
            await self.empty_control_socket()
            await self.inject_without_lock(inject_data)
            try:
                # 剪切板为空时，此处为堵塞
                _meta = await asyncio.wait_for(self.device.control_socket.read_exactly(5), 1)
                msg_type, msg_lens = struct.unpack('>BI', _meta)
                return await self.device.control_socket.read_exactly(msg_lens)
            except Exception as e:
                print(f'no clipborad ! {e}')
                return b''

    async def set_clipboard(self, text, sequence=1, paste=True):
        """
        sequence: 序列号用于标识复制是否成功。不为0时，set_clipboard成功后scrcpy会返回这个sequence
        paste: if input widget is focus, auto paste
        inject_data: lens 10 + *
        """
        msg_type = sc_control_msg_type.SC_CONTROL_MSG_TYPE_SET_CLIPBOARD
        byte_data = text.encode("utf-8")
        inject_data = struct.pack(">BQ?I", msg_type, sequence, paste, len(byte_data)) + byte_data
        async with self.device.device_lock:
            await self.empty_control_socket()
            await self.inject_without_lock(inject_data)
            sequence = (await self.device.control_socket.read_exactly(9))[1:]
            return sequence

    async def set_screen_power_mode(self, screen_power_mode=sc_screen_power_mode.SC_SCREEN_POWER_MODE_NORMAL):
        """
        inject_data: lens 2
        """
        msg_type = sc_control_msg_type.SC_CONTROL_MSG_TYPE_SET_SCREEN_POWER_MODE
        inject_data = struct.pack(">BB", msg_type, screen_power_mode)
        await self.inject_without_lock(inject_data)
        return inject_data

    async def swipe(self, x, y, end_x, end_y, resolution, unit=5, delay=1):
        """
        swipe (x,y) to (end_x, end_y), 匀速移动，每unit个像素点出发一次touch move事件
        """
        x_1, y_1 = x, y
        end_x, end_y = min(end_x, resolution[0]), min(end_y, resolution[1])
        step = 1
        while True:
            if x_1 > end_x:
                x_1 -= min(x-end_x, unit)
            elif x_1 < end_x:
                x_1 += min(end_x-x_1, unit)
            if y_1 > end_y:
                y_1 -= min(y_1-end_y, unit)
            elif y < end_y:
                y_1 += min(end_y-y_1, unit)
            if x_1 == end_x and y_1 == end_y:
                break
            step += 1
        unit_delay = delay/step
        await self.inject_touch_event(x, y, resolution, android_motionevent_action.AMOTION_EVENT_ACTION_DOWN)
        while True:
            if x > end_x:
                x -= min(x-end_x, unit)
            elif x < end_x:
                x += min(end_x-x, unit)
            if y > end_y:
                y -= min(y-end_y, unit)
            elif y < end_y:
                y += min(end_y-y, unit)
            await self.inject_touch_event(x, y, resolution, android_motionevent_action.AMOTION_EVENT_ACTION_MOVE)
            await asyncio.sleep(unit_delay)
            if x == end_x and y == end_y:
                await self.inject_touch_event(x, y, resolution, android_motionevent_action.AMOTION_EVENT_ACTION_UP)
                break


class DeviceClient:
    # 录屏工具
    recorder = DeviceRecorder
    recorder.start_server()
    # socket超时时间,毫秒
    connect_timeout = 300

    def __init__(self, ws_client, ws_session_id):
        self.ws_session_id = ws_session_id
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
        self.controller = DeviceController(self)
        # 需要推流的ws_client
        self.ws_client = ws_client
        # 录屏相关
        self.recorder_enable = self.scrcpy_kwargs.pop('recorder_enable', None)
        self.recorder_format = self.scrcpy_kwargs.pop('recorder_format', None)
        self.recorder_ctx = None
        self.recorder_socket = None
        self.recorder_start_time = None
        self.recorder_finish_time = None

    async def cancel_task(self, task):
        logging.info(f"【DeviceClient】({self.device_id}:{self.ws_session_id}) task cancel {task}")
        # If task is already finish, this operation will return False, else return True(mean cancel operation success)
        task.cancel()
        try:
            # Wait task done, Exception inside the task will raise here
            await task
            # [task cancel operation no effect] 1.task already finished
        except asyncio.CancelledError:
            # [task cancel operation success] 2.catch task CancelledError Exception
            logging.error(f"【DeviceClient】({self.device_id}:{self.ws_session_id}) task is cancelled now")
        except Exception as e:
            # [task cancel operation no effect] 3.task already finished with a normal Exception
            logging.error(f"【DeviceClient】({self.device_id}:{self.ws_session_id}) task await exception {type(e)}, {e}")

    async def shell(self, command):
        if isinstance(command, list):
            command = ' '.join(command)
        command = command.replace('True', 'true').replace('False', 'false')
        shell_socket = await self.adb_device.create_shell_socket(command)
        return shell_socket

    async def deploy_server(self):
        # 1.推送jar包
        server_file_path = os.path.join(BASE_DIR, "asset/scrcpy-server-v2.0")
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
            if accept_audio_encode == b'\x00\x00\x00\x00':
                logging.error(f"【DeviceClient】({self.device_id}:{self.ws_session_id}) open audio error, has Android >==11?")
                self.scrcpy_kwargs['audio'] = False
                await self.audio_socket.disconnect()
                self.audio_socket = None
        else:
            await self.send_to_recorder(struct.pack(">L", 0))

    async def _deploy_task(self):
        while True:
            data = await self.deploy_socket.read_string_line()
            if not data:
                break
            logging.info(f"【DeviceClient】({self.device_id}:{self.ws_session_id})" + data.rstrip('\r\n').rstrip('\n'))

    async def _video_task(self):
        try:
            while True:
                # 1.读取frame_meta
                frame_meta = await self.video_socket.read_exactly(12)
                data_length = struct.unpack('>L', frame_meta[8:])[0]
                current_nal_data = await self.video_socket.read_exactly(data_length)
                # 2.向录屏工具发送当前nal
                await self.send_to_recorder(frame_meta+current_nal_data)
                # 3.向前端发送当前nal
                await self.ws_client.send(bytes_data=current_nal_data)
        finally:
            # 多次调用ws-close，有且只有一次会生效，所以ws-client的disconnect方法只会执行一次，即stop方法只执行一次
            await self.ws_client.close()

    async def _audio_task(self):
        is_raw = self.scrcpy_kwargs['audio_codec'] == 'raw'
        is_opus = self.scrcpy_kwargs['audio_codec'] == 'opus'
        is_acc = self.scrcpy_kwargs['audio_codec'] == 'aac'
        try:
            while True:
                # 1.读取frame_meta
                frame_meta = await self.audio_socket.read_exactly(12)
                data_length = struct.unpack('>L', frame_meta[8:])[0]
                current_nal_data = await self.audio_socket.read_exactly(data_length)
                # 2.向录屏工具发送当前nal
                await self.send_to_recorder(frame_meta + current_nal_data)
                # 3.向前端发送当前nal
                # any(b'\x00\x00') is False
                if is_raw and (not any(current_nal_data)): 
                    continue
                elif is_opus and (current_nal_data == b'\xfc\xff\xfe'):
                    continue
                elif is_acc and (current_nal_data.find(b'ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ')>=0):
                    continue
                await self.ws_client.send(bytes_data=format_audio_data(current_nal_data))
        finally:
            # 多次调用ws-close，有且只有一次会生效，所以ws-client的disconnect方法只会执行一次，即stop方法只执行一次
            await self.ws_client.close()

    # check login state
    async def check_login_task(self):
        while True:
            await asyncio.sleep(5)
            if not await self.ws_client.check_login():
                return
            if not self.video_socket:
                return

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
        if self.recorder_enable:
            cmd = os.path.join(BASE_DIR, 'asset/recorder.out')
            args = [f'{self.ws_session_id}.{self.recorder_format}', '127.0.0.1', '45678', 'media/video/']
            self.recorder_ctx = await asyncio.create_subprocess_exec(cmd, *args, stdout=asyncio.subprocess.PIPE, stderr=sys.stderr)
            for _ in range(200):
                await asyncio.sleep(0.01)
                if self.ws_session_id in self.recorder.RECORDER_CLIENT_SOCKET:
                    self.recorder_socket = self.recorder.RECORDER_CLIENT_SOCKET[self.ws_session_id]
                    logging.info(f"【DeviceClient】({self.device_id}:{self.ws_session_id}) recorder_success recorder_socket")
                    break
            else:
                logging.error(f"【DeviceClient】({self.device_id}:{self.ws_session_id}) recorder_error recorder_socket")

    async def send_to_recorder(self, data):
        if self.recorder_socket:
            try:
                await self.recorder_socket.write(data)
            except Exception as e:
                await self.stop_recorder()

    async def stop_recorder(self):
        if self.recorder_socket:
            recorder_filename = os.path.join(MEDIA_ROOT, 'video', f"{self.ws_session_id}.{self.recorder_format}")
            try:
                from general.models import Video
                self.recorder_socket = None
                await self.recorder.del_recorder_socket(self.ws_session_id)
                await self.recorder_ctx.wait()
                stdout, stderr = await self.recorder_ctx.communicate()
                stdout_msg = stdout.decode('utf-8')
                logging.info(f"【DeviceClient】({self.device_id}:{self.ws_session_id}) {stdout_msg}")
                duration = int(re.search(r"视频时长:(\d+)秒!!", stdout_msg).group(1))
                data = dict(
                    video_id=self.ws_session_id,
                    device_id=self.device_id,
                    format=self.recorder_format,
                    duration=duration,
                    size=int(os.path.getsize(recorder_filename)/ 1024),
                    start_time=self.recorder_start_time,
                    finish_time=self.recorder_finish_time,
                    config=json.dumps(self.scrcpy_kwargs)
                )
                await Video.objects.acreate(**data)
            except Exception as e:
                logging.error(f"【DeviceClient】({self.device_id}:{self.ws_session_id}) recorder_error stop_recorder {type(e)}: {str(e)}")
                self.recorder_socket = None
                if self.ws_session_id in self.recorder.RECORDER_CLIENT_SOCKET:
                    del self.recorder.RECORDER_CLIENT_SOCKET[self.ws_session_id]
                try:
                    os.remove(recorder_filename)
                except:
                    pass

    async def start(self):
        logging.info(f"【DeviceClient】({self.device_id}:{self.ws_session_id}) =======> start {self.scrcpy_kwargs}")
        # 1.start deploy server
        logging.info(f"【DeviceClient】({self.device_id}:{self.ws_session_id}) (1).start deploy")
        await self.deploy_server()
        self.deploy_task = asyncio.create_task(self._deploy_task())
        # 2.start_recorder
        logging.info(f"【DeviceClient】({self.device_id}:{self.ws_session_id}) (2).start recorder")
        await self.start_recorder()
        # 3.create socket and get first config nal
        logging.info(f"【DeviceClient】({self.device_id}:{self.ws_session_id}) (3).start socket")
        await self.create_socket()
        self.recorder_start_time = datetime.datetime.now()
        await self.handle_first_config_nal()
        # 4.video task
        logging.info(f"【DeviceClient】({self.device_id}:{self.ws_session_id}) (4).start video task")
        self.video_task = asyncio.create_task(self._video_task())
        # 5.audio task
        if self.scrcpy_kwargs['audio']:
            logging.info(f"【DeviceClient】({self.device_id}:{self.ws_session_id}) (5).start audio task")
            self.audio_task = asyncio.create_task(self._audio_task())
        # 6.check login task
        # self.video_task = asyncio.create_task(self.check_login_task())

    async def stop(self):
        try:
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
        finally:
            # 5.stop_recorder
            await self.stop_recorder()
        logging.info(f"【DeviceClient】({self.device_id}:{self.ws_session_id}) =======> stopped")
