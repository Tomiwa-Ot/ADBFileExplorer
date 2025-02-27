# ADB File Explorer `tool`
# Copyright (C) 2022  Azat Aldeshov azata1919@gmail.com
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from typing import List

from core.configurations import Defaults
from core.managers import AndroidADBManager
from data.models import FileType, Device, File
from helpers.converters import convert_to_devices, convert_to_file, convert_to_file_list_a
from services import adb


class FileRepository:
    @classmethod
    def file(cls, path: str) -> (File, str):
        if not AndroidADBManager.get_device():
            return None, "No device selected!"

        path = AndroidADBManager.clear_path(path)
        args = adb.ShellCommand.LS_LIST_DIRS + [path.replace(' ', r'\ ')]
        response = adb.shell(AndroidADBManager.get_device().id, args)
        if not response.IsSuccessful:
            return None, response.ErrorData or response.OutputData

        file = convert_to_file(response.OutputData.strip())
        if not file:
            return None, f"Unexpected string:\n{response.OutputData}"

        if file.type == FileType.LINK:
            args = adb.ShellCommand.LS_LIST_DIRS + [path.replace(' ', r'\ ') + '/']
            response = adb.shell(AndroidADBManager.get_device().id, args)
            file.link_type = FileType.UNKNOWN
            if response.OutputData and response.OutputData.startswith('d'):
                file.link_type = FileType.DIRECTORY
            elif response.OutputData and response.OutputData.__contains__('Not a'):
                file.link_type = FileType.FILE
        file.path = path
        return file, response.ErrorData

    @classmethod
    def files(cls) -> (List[File], str):
        if not AndroidADBManager.get_device():
            return None, "No device selected!"

        path = AndroidADBManager.path()
        args = adb.ShellCommand.LS_ALL_LIST + [path.replace(' ', r'\ ')]
        response = adb.shell(AndroidADBManager.get_device().id, args)
        if not response.IsSuccessful and response.ExitCode != 1:
            return [], response.ErrorData or response.OutputData

        if not response.OutputData:
            return [], response.ErrorData

        args = adb.ShellCommand.LS_ALL_DIRS + [path.replace(' ', r'\ ') + "*/"]
        response_dirs = adb.shell(AndroidADBManager.get_device().id, args)
        if not response_dirs.IsSuccessful and response_dirs.ExitCode != 1:
            return [], response_dirs.ErrorData or response_dirs.OutputData

        dirs = response_dirs.OutputData.split() if response_dirs.OutputData else []
        files = convert_to_file_list_a(response.OutputData, dirs=dirs, path=path)
        return files, response.ErrorData

    @classmethod
    def rename(cls, file: File, name) -> (str, str):
        if name.__contains__('/') or name.__contains__('\\'):
            return None, "Invalid name"
        args = [adb.ShellCommand.MV, file.path.replace(' ', r'\ '), (file.location + name).replace(' ', r'\ ')]
        response = adb.shell(AndroidADBManager.get_device().id, args)
        return None, response.ErrorData or response.OutputData

    @classmethod
    def open_file(cls, file: File) -> (str, str):
        args = [adb.ShellCommand.CAT, file.path.replace(' ', r'\ ')]
        if file.isdir:
            return None, f"Can't open. {file.path} is a directory"
        response = adb.shell(AndroidADBManager.get_device().id, args)
        if not response.IsSuccessful:
            return True, response.ErrorData or response.OutputData
        return None, response.ErrorData or response.OutputData

    @classmethod
    def delete(cls, file: File) -> (str, str):
        args = [adb.ShellCommand.RM, file.path.replace(' ', r'\ ')]
        if file.isdir:
            args = adb.ShellCommand.RM_DIR_FORCE + [file.path.replace(' ', r'\ ')]
        response = adb.shell(AndroidADBManager.get_device().id, args)
        if not response.IsSuccessful or response.OutputData:
            return None, response.ErrorData or response.OutputData
        return f"{'Folder' if file.isdir else 'File'} '{file.path}' has been deleted", None

    @classmethod
    def download(cls, progress_callback: callable, source: str) -> (str, str):
        destination = Defaults.device_downloads_path(AndroidADBManager.get_device())
        return cls.download_to(progress_callback, source, destination)

    class UpDownHelper:
        def __init__(self, callback: callable):
            self.messages = []
            self.callback = callback

        def call(self, data: str):
            if data.startswith('['):
                progress = data[1:4].strip()
                if progress.isdigit():
                    self.callback(data[7:], int(progress))
            elif data:
                self.messages.append(data)

    @classmethod
    def download_to(cls, progress_callback: callable, source: str, destination: str) -> (str, str):
        if AndroidADBManager.get_device() and source and destination:
            helper = cls.UpDownHelper(progress_callback)
            response = adb.pull(AndroidADBManager.get_device().id, source, destination, helper.call)
            if not response.IsSuccessful:
                return None, response.ErrorData or "\n".join(helper.messages)

            return "\n".join(helper.messages), response.ErrorData
        return None, None

    @classmethod
    def new_folder(cls, name) -> (str, str):
        if not AndroidADBManager.get_device():
            return None, "No device selected!"

        args = [adb.ShellCommand.MKDIR, f'{AndroidADBManager.path()}{name}'.replace(' ', r"\ ")]
        response = adb.shell(AndroidADBManager.get_device().id, args)
        if not response.IsSuccessful:
            return None, response.ErrorData or response.OutputData
        return response.OutputData, response.ErrorData

    @classmethod
    def upload(cls, progress_callback: callable, source: str) -> (str, str):
        if AndroidADBManager.get_device() and AndroidADBManager.path() and source:
            helper = cls.UpDownHelper(progress_callback)
            response = adb.push(AndroidADBManager.get_device().id, source, AndroidADBManager.path(), helper.call)
            if not response.IsSuccessful:
                return None, response.ErrorData or "\n".join(helper.messages)

            return "\n".join(helper.messages), response.ErrorData
        return None, None


class DeviceRepository:
    @classmethod
    def devices(cls) -> (List[Device], str):
        response = adb.devices()
        if not response.IsSuccessful:
            return [], response.ErrorData or response.OutputData

        devices = convert_to_devices(response.OutputData)
        return devices, response.ErrorData

    @classmethod
    def connect(cls, device_id) -> (str, str):
        if not device_id:
            return None, None

        response = adb.connect(device_id)
        if not response.IsSuccessful:
            return None, response.ErrorData or response.OutputData
        return response.OutputData, response.ErrorData

    @classmethod
    def disconnect(cls) -> (str, str):
        response = adb.disconnect()
        if not response.IsSuccessful:
            return None, response.ErrorData or response.OutputData

        return response.OutputData, response.ErrorData
