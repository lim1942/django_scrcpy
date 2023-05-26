import stat
import struct
import asyncio
import datetime

from asynch.tools.utils import AsyncSocket
from django_scrcpy.settings import ADB_SERVER_ADDR, ADB_SERVER_PORT


class AdbError(Exception):
    pass


class AsyncAdbSocket(AsyncSocket):
    async def connect(self):
        try:
            self.reader, self.writer = await asyncio.wait_for(asyncio.open_connection(ADB_SERVER_ADDR, ADB_SERVER_PORT), self.socket_timeout)
        except Exception as e:
            await self.disconnect()
            if isinstance(e, asyncio.CancelledError):
                raise e


class AsyncAdbDevice:
    _OKAY = "OKAY"
    _FAIL = "FAIL"
    _DENT = "DENT"  # Directory Entity
    _DONE = "DONE"
    _DATA = "DATA"

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
                await socket.write(self.cmd_format(f'host:transport:{self.device_id}'))
                assert await socket.read_exactly(4) == b'OKAY'
                await socket.write(self.cmd_format(connect_name))
                assert await socket.read_exactly(4) == b'OKAY'
                return socket
            except Exception as e:
                await socket.disconnect()
                if isinstance(e, asyncio.CancelledError):
                    raise e
            await asyncio.sleep(0.01)
        else:
            raise ConnectionError(f"{self.device_id} create_connection to {connect_name} error!!")

    async def create_shell_socket(self, command, timeout=300):
        socket = self.get_adb_socket()
        for _ in range(timeout):
            try:
                await socket.connect()
                await socket.write(self.cmd_format(f'host:transport:{self.device_id}'))
                assert await socket.read_exactly(4) == b'OKAY'
                await socket.write(self.cmd_format('shell:{}'.format(command)))
                assert await socket.read_exactly(4) == b'OKAY'
                return socket
            except Exception as e:
                await socket.disconnect()
                if isinstance(e, asyncio.CancelledError):
                    raise e
            await asyncio.sleep(0.01)
        else:
            raise ConnectionError(f"{self.device_id} create_shell error!!")

    async def shell(self, command, stream=False):
        socket = await self.create_shell_socket(command)
        if stream:
            return socket
        else:
            data = await socket.read_string(-1)
            await socket.disconnect()
            return data

    async def create_sync_socket(self, path, command, timeout=300):
        socket = self.get_adb_socket()
        for _ in range(timeout):
            try:
                await socket.connect()
                await socket.write(self.cmd_format(f'host:transport:{self.device_id}'))
                assert await socket.read_exactly(4) == b'OKAY'
                await socket.write(self.cmd_format('sync:'))
                assert await socket.read_exactly(4) == b'OKAY'
                await socket.write(command.encode("utf-8") + struct.pack("<I", len(path.encode('utf-8'))) + path.encode("utf-8"))
                return socket
            except Exception as e:
                await socket.disconnect()
                if isinstance(e, asyncio.CancelledError):
                    raise e
            await asyncio.sleep(0.01)
        else:
            raise ConnectionError(f"{self.device_id} create_sync error!!")

    async def stat(self, path):
        socket = await self.create_sync_socket(path, 'STAT')
        try:
            assert "STAT" == await socket.read_string_exactly(4)
            mode, size, mtime = struct.unpack("<III", await socket.read_exactly(12))
            mtime = datetime.datetime.fromtimestamp(mtime) if mtime else None
            return {'mtime': mtime, 'mode': mode, 'size': size}
        finally:
            await socket.disconnect()

    async def iter_directory(self, path):
        socket = await self.create_sync_socket(path, 'LIST')
        try:
            while True:
                resp = await socket.read_string_exactly(4)
                if resp == self._DONE:
                    break
                meta = await socket.read_exactly(16)
                mode, size, mtime, namelen = struct.unpack("<IIII", meta)
                name = await socket.read_string_exactly(namelen)
                try:
                    mtime = datetime.datetime.fromtimestamp(mtime)
                except OSError:     # bug in Python 3.6
                    mtime = datetime.datetime.now()
                yield {'name': '/'.join([path, name]), 'mtime': mtime, 'mode': mode, 'size': size}
        finally:
            await socket.disconnect()

    async def list_directory(self, path):
        return [_ async for _ in self.iter_directory(path)]

    async def push_file(self, src, dst, mode=0o755, check=True):
        path = dst + "," + str(stat.S_IFREG | mode)
        socket = await self.create_sync_socket(path, 'SEND')
        try:
            with open(src, 'rb') as f:
                total_size = 0
                while True:
                    chunk = f.read(4096)
                    if not chunk:
                        mtime = int(datetime.datetime.now().timestamp())
                        await socket.write(b"DONE" + struct.pack("<I", mtime))
                        break
                    await socket.write(b"DATA" + struct.pack("<I", len(chunk)))
                    await socket.write(chunk)
                    total_size += len(chunk)
                status_msg = await socket.read_string_exactly(4)
                await socket.disconnect()
                if status_msg != self._OKAY:
                    raise AdbError("上传文件失败")
            if check:
                file_size = (await self.stat(dst))['size']
                if file_size != total_size:
                    raise AdbError("上传文件失败,check失败")
        finally:
            await socket.disconnect()

    async def iter_content(self, path):
        socket = await self.create_sync_socket(path, 'RECV')
        try:
            while True:
                status_msg = await socket.read_string_exactly(4)
                if status_msg == self._FAIL:
                    error_msg_size = struct.unpack("<I", await socket.read_exactly(4))[0]
                    error_msg = await socket.read_string_exactly(error_msg_size)
                    raise AdbError(f"iter_content error {error_msg}")
                elif status_msg == self._DONE:
                    break
                elif status_msg == self._DATA:
                    chunk_size = struct.unpack("<I", await socket.read_exactly(4))[0]
                    chunk = await socket.read_exactly(chunk_size)
                    if len(chunk) != chunk_size:
                        raise RuntimeError("read chunk missing")
                    yield chunk
                else:
                    raise AdbError(f"Invalid sync cmd {path}")
        finally:
            await socket.disconnect()

    async def get_content(self, path):
        return b''.join([_ async for _ in self.iter_content(path)])


if __name__ == '__main__':
    async def test_shell():
        adb_device = AsyncAdbDevice('ea141ba00521')
        a = await adb_device.shell('top', stream=True)
        while True:
            print(await a.read_string_line())
    async def test_list_directory():
        adb_device = AsyncAdbDevice('ea141ba00521')
        print(await adb_device.list_directory('/sdcard'))
    async def test_push_file():
        adb_device = AsyncAdbDevice('ea141ba00521')
        await adb_device.push_file('scrcpy-server-v1.24', '/sdcard/ccccc')
    async def test_get_content():
        adb_device = AsyncAdbDevice('ea141ba00521')
        print(await adb_device.get_content( '/sdcard/ccccc'))

    asyncio.run(test_get_content())

