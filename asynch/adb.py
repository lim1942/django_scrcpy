import asyncio
from django_scrcpy.settings import ADB_SERVER_ADDR, ADB_SERVER_PORT


class AsyncAdbSocket:
    def __init__(self, socket_timeout=1):
        self.socket_timeout = socket_timeout
        self.reader = None
        self.writer = None

    async def connect(self):
        try:
            self.reader, self.writer = await asyncio.wait_for(asyncio.open_connection(ADB_SERVER_ADDR, ADB_SERVER_PORT), self.socket_timeout)
        except:
            await self.disconnect()

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


class AsyncAdbDevice:
    @classmethod
    def cmd_format(cls, cmd):
        return "{:04x}{}".format(len(cmd), cmd).encode("utf-8")

    def __init__(self, device_id, socket_timeout=1):
        self.device_id = device_id
        self.socket_timeout = socket_timeout

    def get_adb_socket(self):
        return AsyncAdbSocket(socket_timeout=self.socket_timeout)

    async def create_connection_socket(self, connect_name, timeout=300):
        socket = self.get_adb_socket()
        for _ in range(timeout):
            try:
                await socket.connect()
                socket.writer.write(self.cmd_format(f'host:transport:{self.device_id}'))
                await socket.writer.drain()
                assert await socket.reader.read(4) == b'OKAY'
                socket.writer.write(self.cmd_format(connect_name))
                await socket.writer.drain()
                assert await socket.reader.read(4) == b'OKAY'
                return socket
            except:
                await socket.disconnect()
            await asyncio.sleep(0.01)
        else:
            raise ConnectionError(f"{self.device_id} create_connection to {connect_name} error!!")

    async def create_shell_socket(self, command, timeout=300):
        socket = self.get_adb_socket()
        for _ in range(timeout):
            try:
                await socket.connect()
                socket.writer.write(self.cmd_format(f'host:transport:{self.device_id}'))
                await socket.writer.drain()
                assert await socket.reader.read(4) == b'OKAY'
                socket.writer.write(self.cmd_format('shell:{}'.format(command)))
                await socket.writer.drain()
                assert await socket.reader.read(4) == b'OKAY'
                return socket
            except:
                await socket.disconnect()
            await asyncio.sleep(0.01)
        else:
            raise ConnectionError(f"{self.device_id} create_shell error!!")


if __name__ == '__main__':
    async def test():
        while True:
            adb_device = AsyncAdbDevice('5b39e4f30207')
            socket = await adb_device.create_shell_socket('top')
            print(await socket.read(1000))
    asyncio.run(test())


