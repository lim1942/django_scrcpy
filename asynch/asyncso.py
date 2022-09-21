import asyncio
from django_scrcpy.settings import ADB_SERVER_ADDR, ADB_SERVER_PORT


class DeviceAsyncSocket:
    @classmethod
    def cmd_format(cls, cmd):
        return "{:04x}{}".format(len(cmd), cmd).encode("utf-8")

    def __init__(self, device_id):
        self.device_id = device_id
        self.reader = None
        self.writer = None

    async def connect(self):
        self.reader, self.writer = await asyncio.open_connection(ADB_SERVER_ADDR, ADB_SERVER_PORT)
        self.writer.write(self.cmd_format(f'host:transport:{self.device_id}'))
        await self.writer.drain()
        assert await self.reader.read(4) == b'OKAY'
        self.writer.write(self.cmd_format('localabstract:scrcpy'))
        await self.writer.drain()
        assert await self.reader.read(4) == b'OKAY'

    async def read(self, cnt=-1):
        return await self.reader.read(cnt)

    async def write(self, data):
        self.writer.write(data)
        await self.writer.drain()

    async def close(self):
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
            self.writer = self.reader = None
