import os.path
import stat
import uuid

import adbutils
from django_scrcpy.settings import ADB_SERVER_ADDR, ADB_SERVER_PORT


class AdbDevice:
    adb = adbutils.AdbClient(host=ADB_SERVER_ADDR, port=int(ADB_SERVER_PORT))

    @classmethod
    def list(cls, slug=False):
        devices = {}
        for item in cls.adb.list():
            adb_item = adbutils.adb.device(serial=item.serial)
            info = dict()
            device_id = item.serial.replace(':', '_').replace('.', ',') if slug else item.serial
            info['device_id'] = device_id
            info['status'] = item.state
            info['online'] = item.state == 'device'
            try:
                info['marketname'] = adb_item.shell(["getprop", "ro.product.marketname"])
            except:
                info['marketname'] = ''
            devices[device_id] = info
        return devices

    def __init__(self, device_id, path_sep='/'):
        self.device_id = device_id.replace(',', '.').replace('_', ':')
        self.path_sep = path_sep
        self.device = adbutils.adb.device(serial=self.device_id)

    def path_join(self, *ps):
        new_p = self.path_sep.join(ps).replace(f"{self.path_sep}{self.path_sep}{self.path_sep}", self.path_sep).\
            replace(f"{self.path_sep}{self.path_sep}", self.path_sep)
        if new_p.endswith(self.path_sep):
            new_p = new_p[:-1]
        return new_p

    def filemanager_list(self, path, contain_dot=False):
        items = []
        for f_info in self.device.sync.list(path):
            if not contain_dot and f_info.path in ['.', '..']:
                continue
            rights = stat.filemode(f_info.mode)
            if rights[0] == '-':
                typ = 'file'
            elif rights[0] == 'd':
                typ = 'dir'
            elif rights[0] == 'l':
                typ = 'link'
            item = {'name': f_info.path, 'rights': rights, 'size': str(f_info.size),
                    'date': f_info.mtime,
                    'type': typ}
            items.append(item)
        return items

    def filemanager_upload(self, destination, files):
        try:
            for _, file in files.items():
                self.device.sync.push(file, self.path_join(destination, file.name))
            return True, None
        except Exception as e:
            return False, str(e)

    def filemanager_rename(self, item, new_item_path):
        ret = self.device.shell(f'mv {item} {new_item_path}')
        return not ret, ret

    def filemanager_copy(self, items, new_path, single_filename=''):
        if single_filename:
            cmd = f'cp {items[0]} {self.path_join(new_path, single_filename)}'
        else:
            items_string = ' '.join(items)
            cmd = f'cp {items_string} {new_path}'
        ret = self.device.shell(cmd)
        return not ret, ret

    def filemanager_move(self, items, new_path):
        items_string = ' '.join(items)
        ret = self.device.shell(f'mv {items_string} {new_path}')
        return not ret, ret

    def filemanager_remove(self, items):
        items_string = ' '.join(items)
        ret = self.device.shell(f'rm -rf {items_string}')
        return not ret, ret

    def filemanager_edit(self, item, content):
        try:
            self.device.sync.push(content, item)
            return True, None
        except Exception as e:
            return False, str(e)

    def filemanager_get_content(self, item):
        return self.device.sync.read_bytes(item)

    def filemanager_iter_content(self, item):
        return self.device.sync.iter_content(item)

    def filemanager_iter_multi_content(self, items):
        compress_dir = os.path.dirname(items[0])
        compressed_filename = f'{uuid.uuid4().hex}.zip'
        self.filemanager_compress(items, compress_dir, compressed_filename=compressed_filename)
        compressed_full_filename = self.path_join(compress_dir, compressed_filename)
        for _ in self.filemanager_iter_content(compressed_full_filename):
            yield _
        self.filemanager_remove([compressed_full_filename])

    def filemanager_create_folder(self, new_path):
        ret = self.device.shell(f'mkdir {new_path}')
        return not ret, ret

    def filemanager_walker(self, filename_or_pathname):
        ret = self.filemanager_list(filename_or_pathname)
        con = []
        if not ret:
            return [filename_or_pathname]
        else:
            for f_or_d in ret:
                item_path = self.path_join(filename_or_pathname, f_or_d['name'])
                if f_or_d['type'] == 'file':
                    con.append(item_path)
                elif f_or_d['type'] == 'dir':
                    con.extend(self.filemanager_walker(item_path))
        return con

    def filemanager_compress(self, items, destination, compressed_filename):
        files = []
        # python3.7 strip bug
        discard_prefix = (destination + self.path_sep).replace(f"{self.path_sep}{self.path_sep}", self.path_sep)
        for item in items:
            for file in self.filemanager_walker(item):
                files.append(file[len(discard_prefix):])
        files_string = ' '.join(files)
        cmd = f'cd {destination} && zip_utils -o {self.path_join(destination, compressed_filename)} {files_string}'
        ret = self.device.shell(cmd)
        if 'error in' not in ret:
            return True, ''
        else:
            return False, ret

    def filemanager_extract(self, item, destination, folder_name):
        unzip_path = self.path_join(destination, folder_name)
        try:
            self.filemanager_create_folder(unzip_path)
        except Exception as e:
            pass
        ret = self.device.shell(f'unzip -d {unzip_path} {item}')
        if 'Archive:' in ret:
            return True, ''
        else:
            return False, ret

    def filemanager_change_permissions(self, items, perms_code, recursive=True):
        cmd = f"chmod {'-R' if recursive else ''} {perms_code} {' '.join(items)}"
        ret = self.device.shell(cmd)
        return not ret, ret


if __name__ == "__main__":
    obj = AdbDevice(device_id='ba406a9e0421')
    # print(obj.filemanager_rename())
    # print(obj.device.shell('mv /sdcard/Download/Pod.pm /sdcard/Download/Pod.pm'))
    # print(obj.filemanager_rename('/sdcard/Download/Pod.pm', '/Pod.pm'))
    # print(obj.filemanager_iter_content('/sdcard/Download/Pod.pm').name)
    # obj.filemanager_upload('/sdcard', {'f1':open('views.py','rb')})
    # print(obj.filemanager_walker('/sdcard/Download/1111'))
    print(obj.filemanager_list('/sdcard/Download'))