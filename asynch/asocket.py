import asyncio
from django_scrcpy.settings import ADB_SERVER_ADDR, ADB_SERVER_PORT


class AsyncAdbSocket:
    @classmethod
    def cmd_format(cls, cmd):
        return "{:04x}{}".format(len(cmd), cmd).encode("utf-8")

    def __init__(self, device_id, connect_name, connect_timeout=300):
        self.device_id = device_id
        self.connect_timeout = connect_timeout
        self.connect_name = connect_name
        self.reader = None
        self.writer = None

    async def _connect(self):
        try:
            self.reader, self.writer = await asyncio.open_connection(ADB_SERVER_ADDR, ADB_SERVER_PORT)
            self.writer.write(self.cmd_format(f'host:transport:{self.device_id}'))
            await self.writer.drain()
            assert await self.reader.read(4) == b'OKAY'
            self.writer.write(self.cmd_format(self.connect_name))
            await self.writer.drain()
            assert await self.reader.read(4) == b'OKAY'
            return True
        except:
            await self.disconnect()

    async def connect(self):
        for _ in range(self.connect_timeout):
            if await self._connect():
                break
            await asyncio.sleep(0.01)
        else:
            raise ConnectionError(f"connect to {self.connect_name} error!!")

    async def read(self, cnt=-1):
        return await self.reader.read(cnt)

    async def read_line(self):
        return await self.reader.readline()

    async def read_exactly(self, cnt):
        return await self.reader.readexactly(cnt)

    async def read_until(self, sep):
        return await self.reader.readuntil(sep)

    async def write(self, data):
        self.writer.write(data)
        await self.writer.drain()

    async def disconnect(self):
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
            self.writer = self.reader = None
