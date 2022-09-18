import time

from channels.generic.websocket import WebsocketConsumer
from common.container import LOCAL_CLIENT_DICT, VIDEO_CLIENT_DICT, CONTROL_CLIENT_DICT, SCRCPY_PROCESS_DICT,\
    modify_video_client_dict, modify_control_client_dict


class MyWebsocketConsumer(WebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.device_id = None


class LocalConsumer(MyWebsocketConsumer):
    def connect(self):
        self.device_id = self.scope['url_route']['kwargs']['device_id']
        LOCAL_CLIENT_DICT[self.device_id] = self
        self.accept()
        print(self, 'local connect')

    def receive(self, text_data=None, bytes_data=None):
        if bytes_data.startswith(b'\x00\x00\x00\x01'):
            for client in VIDEO_CLIENT_DICT[self.device_id]:
                client.send(bytes_data)
        else:
            for client in CONTROL_CLIENT_DICT[self.device_id]:
                client.send(bytes_data)

    def disconnect(self, code):
        del LOCAL_CLIENT_DICT[self.device_id]
        print(self, 'local disconnect')


class VideoConsumer(MyWebsocketConsumer):
    def connect(self):
        print(self, 'video connect')
        self.accept()
        self.device_id = self.scope['url_route']['kwargs']['device_id']
        modify_video_client_dict(self.device_id, self)

    def receive(self, text_data=None, bytes_data=None):
        print(text_data)
        print(bytes_data)
        time.sleep(10)

    def disconnect(self, code):
        print(code)
        modify_video_client_dict(self.device_id, self, add=False)
        print(self, 'video disconnect')


class ControlConsumer(MyWebsocketConsumer):
    def connect(self):
        self.accept()
        print(self, 'control connect')
        self.device_id = self.scope['url_route']['kwargs']['device_id']
        modify_control_client_dict(self.device_id, self)

    def receive(self, text_data=None, bytes_data=None):
        try:
            LOCAL_CLIENT_DICT[self.device_id].send(bytes_data)
        except:
            pass
        print(text_data)
        print(bytes_data)

    def disconnect(self, code):
        modify_control_client_dict(self.device_id, self, add=False)
        print(self, 'control disconnect')

