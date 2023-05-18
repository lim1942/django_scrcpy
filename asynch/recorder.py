import asyncio
import threading
from asynch.nettool import AsyncSocket


class RecorderTool:
    SERVER_PORT = 8888
    SERVER_HOST = '0.0.0.0'
    RECORDER_CLIENT_SOCKET = {}

    @classmethod
    async def accept(cls, reader, writer):
        recorder_client = AsyncSocket(reader=reader, writer=writer)
        session_id = await recorder_client.read_string_exactly(6)
        cls.RECORDER_CLIENT_SOCKET[session_id] = recorder_client
        print(f"RecorderServer accept client {session_id}")

    @classmethod
    async def _start_server(cls):
        server = await asyncio.start_server(cls.accept, cls.SERVER_HOST, cls.SERVER_PORT)
        async with server:
            await server.serve_forever()

    @classmethod
    def start_server(cls):
        def task(loop):
            asyncio.set_event_loop(loop)
            asyncio.run(cls._start_server())
        new_loop = asyncio.new_event_loop()
        thread = threading.Thread(target=task, args=(new_loop,))
        thread.start()
        print(f"RecorderServer start on {cls.SERVER_HOST}:{cls.SERVER_PORT}")

    @classmethod
    def get_recorder_socket(cls, session_id):
        return cls.RECORDER_CLIENT_SOCKET[session_id]

    @classmethod
    async def del_recorder_socket(cls, session_id):
        if session_id in cls.RECORDER_CLIENT_SOCKET:
            await cls.RECORDER_CLIENT_SOCKET[session_id].disconnect()
            del cls.RECORDER_CLIENT_SOCKET[session_id]
