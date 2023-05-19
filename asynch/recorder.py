import asyncio
import threading
from asynch.nettool import AsyncSocket


class RecorderTool:
    SERVER_PORT = 45678
    SERVER_HOST = '0.0.0.0'
    RECORDER_CLIENT_SOCKET = {}
    EVENT_LOOP = asyncio.new_event_loop()

    @classmethod
    async def accept(cls, reader, writer):
        recorder_client = AsyncSocket(reader=reader, writer=writer)
        session_id = await recorder_client.read_string_exactly(32)
        cls.RECORDER_CLIENT_SOCKET[session_id] = recorder_client
        print(f"RecorderServer accept client {session_id}")

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
        print(f"RecorderServer start on {cls.SERVER_HOST}:{cls.SERVER_PORT}")

    @classmethod
    def get_recorder_socket(cls, session_id):
        return cls.RECORDER_CLIENT_SOCKET[session_id]

    @classmethod
    async def del_recorder_socket(cls, session_id):
        cls.RECORDER_CLIENT_SOCKET[session_id].writer.write_eof()
        await cls.RECORDER_CLIENT_SOCKET[session_id].writer.drain()
        del cls.RECORDER_CLIENT_SOCKET[session_id]


if __name__ == "__main__":
    RecorderTool.start_server()
