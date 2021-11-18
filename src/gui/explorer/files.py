import sys

from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtWidgets import QMenu, QAction, QMessageBox, QFileDialog, QWidget

from config import Resource
from gui.abstract.base import BaseListItemWidget, BaseListWidget, BaseListHeaderWidget
from gui.others.additional import LoadingWidget
from services.data.managers import FileManager, Global
from services.data.models import File, FileType
from services.data.repositories import FileRepository


class FileHeaderWidget(BaseListHeaderWidget):
    def __init__(self):
        super(FileHeaderWidget, self).__init__()

        self.layout.addWidget(
            BaseListItemWidget.name('File', margin=48)
        )

        self.layout.addWidget(
            self.property('Permissions', alignment=Qt.AlignCenter)
        )

        self.layout.addWidget(
            self.property('Size', alignment=Qt.AlignCenter)
        )

        self.layout.addWidget(
            self.property('Date', alignment=Qt.AlignCenter, stretch=3)
        )


class FileListWidget(BaseListWidget):
    def __init__(self, explorer):
        super(FileListWidget, self).__init__()
        self.explorer = explorer

    def update(self):
        super(FileListWidget, self).update()
        files, error = FileRepository.files()
        if error:
            print(error, file=sys.stderr)
        if error and not files:
            QMessageBox.critical(self, 'Files', error)
        Global().communicate.path_toolbar__refresh.emit()

        widgets = []
        for file in files:
            item = FileItemWidget(file, self.explorer)
            widgets.append(item)
        self.load(widgets, "Folder is empty")


class FileItemWidget(BaseListItemWidget):
    def __init__(self, file: File, explorer):
        super(FileItemWidget, self).__init__()
        self.file = file
        self.explorer = explorer
        self.loading = QWidget()
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.context_menu)

        self.layout.addWidget(
            self.icon(self.icon_path)
        )

        self.layout.addWidget(
            self.name(self.file.name)
        )

        self.layout.addWidget(self.separator())

        self.layout.addWidget(
            self.property(self.file.permissions, font_style="italic", alignment=Qt.AlignCenter)
        )

        self.layout.addWidget(self.separator())

        self.layout.addWidget(
            self.property(self.file.size, alignment=Qt.AlignCenter)
        )

        self.layout.addWidget(self.separator())

        self.layout.addWidget(
            self.property(self.file.date, alignment=Qt.AlignCenter, stretch=3)
        )

        self.setToolTip(self.file.name)
        if self.file.type == FileType.LINK:
            self.setToolTip(self.file.link)

    @property
    def icon_path(self):
        if self.file.type == FileType.DIRECTORY:
            return Resource.icon_folder
        elif self.file.type == FileType.FILE:
            return Resource.icon_file
        elif self.file.type == FileType.LINK:
            if self.file.link_type == FileType.DIRECTORY:
                return Resource.icon_link_folder
            elif self.file.link_type == FileType.FILE:
                return Resource.icon_link_file
            return Resource.icon_link_file_unknown
        return Resource.icon_file_unknown

    def mouseReleaseEvent(self, event):
        super(FileItemWidget, self).mouseReleaseEvent(event)

        if event.button() == Qt.LeftButton:
            if FileManager.open(self.file):
                self.parent().update()

    def context_menu(self, pos: QPoint):
        menu = QMenu()
        menu.addSection("Actions")

        action_copy = QAction('Copy to...', self)
        action_copy.setDisabled(True)
        menu.addAction(action_copy)

        action_move = QAction('Move to...', self)
        action_move.setDisabled(True)
        menu.addAction(action_move)

        action_rename = QAction('Rename', self)
        action_rename.setDisabled(True)
        menu.addAction(action_rename)

        action_delete = QAction('Delete', self)
        action_delete.setDisabled(True)
        menu.addAction(action_delete)

        action_download = QAction('Download', self)
        action_download.triggered.connect(self.download)
        menu.addAction(action_download)

        action_download_to = QAction('Download to...', self)
        action_download_to.triggered.connect(self.download_to)
        menu.addAction(action_download_to)

        menu.addSeparator()

        action_properties = QAction('Properties', self)
        action_properties.triggered.connect(self.file_properties)
        menu.addAction(action_properties)

        menu.exec(self.mapToGlobal(pos))

    def download(self):
        self.loading = LoadingWidget(self, 'Downloading... Please wait')
        FileRepository.download(self.file.path, self.__download__)

    def download_to(self):
        dir_name = QFileDialog.getExistingDirectory(self, 'Download to', '~')

        if dir_name:
            self.loading = LoadingWidget(self, 'Downloading... Please wait')
            FileRepository.download_to(self.file.path, dir_name, self.__download__)

    def __download__(self, code, error):
        self.loading.close()
        del self.loading

        if error or code != 0:
            QMessageBox.critical(self, 'Download', error or 'Failed to download! Check the terminal')
        else:
            QMessageBox.information(self, 'Download', "Successfully downloaded!")

    def file_properties(self):
        info = f"<br/><u><b>{str(self.file)}</b></u><br/>"
        info += f"<pre>Name:        {self.file.name or '-'}</pre>"
        info += f"<pre>Owner:       {self.file.owner or '-'}</pre>"
        info += f"<pre>Group:       {self.file.group or '-'}</pre>"
        info += f"<pre>Size:        {self.file.size or '-'}</pre>"
        info += f"<pre>Permissions: {self.file.permissions or '-'}</pre>"
        info += f"<pre>Date:        {self.file.date__raw or '-'}</pre>"
        info += f"<pre>Type:        {self.file.type or '-'}</pre>"

        if self.file.type == FileType.LINK:
            info += f"<pre>Links to:    {self.file.link or '-'}</pre>"

        QMessageBox.information(self, 'Properties', info)
