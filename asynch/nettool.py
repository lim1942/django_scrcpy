class AsyncSocket:
    def __init__(self, socket_timeout=1, reader=None, writer=None):
        self.socket_timeout = socket_timeout
        self.reader = reader
        self.writer = writer

    async def read(self, cnt=-1):
        return await self.reader.read(cnt)

    async def read_line(self):
        return await self.reader.readline()

    async def read_exactly(self, cnt):
        return await self.reader.readexactly(cnt)

    async def read_until(self, sep):
        return await self.reader.readuntil(sep)

    async def read_string(self, cnt=-1, encoding='utf-8'):
        return (await self.reader.read(cnt)).decode(encoding)

    async def read_string_line(self, encoding='utf-8'):
        return (await self.reader.readline()).decode(encoding)

    async def read_string_exactly(self, cnt, encoding='utf-8'):
        return (await self.reader.readexactly(cnt)).decode(encoding)

    async def read_string_until(self, sep, encoding='utf-8'):
        return (await self.reader.readuntil(sep)).decode(encoding)

    async def write(self, data):
        self.writer.write(data)
        await self.writer.drain()

    async def disconnect(self):
        if self.writer:
            self.writer.close()
            try:
                await self.writer.wait_closed()
            except ConnectionAbortedError:
                pass
            self.writer = self.reader = None
