import datetime
import random
from PySide6.QtCore import (
    Qt,
    QAbstractTableModel,
    QDateTime,
    QLocale,
    QModelIndex,
    QProcess,
    QSortFilterProxyModel,
)
from PySide6.QtGui import (
    QColor
)
from .alpm import HEADERS, Paclog, PaclogWarn


def _colors_generate(logs):
    for transaction in set([i.transaction for i in logs]):
        color = QColor(random.randint(0, 255),random.randint(0, 255),random.randint(0, 255),random.randint(80, 200))
        for log in (i for i in logs if i.transaction == transaction):
            log.color = color

class MainModel(QAbstractTableModel):

    def __init__(self, data: list[Paclog], days: int):
        super().__init__()
        self._data = data
        # some entries in log not have package field
        runner = QProcess()
        for item in (l for l in self._data if isinstance(l, PaclogWarn) and not l.package):
            file_ = item.get_file()
            if not file_: continue
            runner.startCommand(f"/usr/bin/pacman -Qoq {file_}")
            runner.waitForFinished()
            if not runner.exitCode():
                if pkg := runner.readAllStandardOutput().toStdString():
                    item.package = pkg
        self.days = days
        _colors_generate(self._data)

    def data(self, index, role):
        if not index.isValid():
            return False
        if role == Qt.ItemDataRole.UserRole and HEADERS[index.column()] == "action":
            return self._data[index.row()].get_ico()
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            return self._data[index.row()][index.column()]
        if role == Qt.ItemDataRole.UserRole + 1:
            return self._data[index.row()]
        if role in (Qt.ItemDataRole.StatusTipRole, Qt.ItemDataRole.ToolTipRole):
            item = self._data[index.row()]
            msg = item.message if isinstance(item, PaclogWarn) else ""
            msg_date = QLocale.system().toString(item.qdate, format=QLocale.FormatType.LongFormat)
            return f"{item.action.name}\t{item.package}\t{msg}\n\t - {msg_date}\n\t - line {item.line:04}"

    def flags(self, index):
        return Qt.ItemNeverHasChildren | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def rowCount(self, index):
        if not self._data:
            return 0
        try:
            return len(self._data)
        except TypeError:
            return 0

    def columnCount(self, index):
        return len(HEADERS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return HEADERS[section].capitalize()
            return chr(section + ord("A"))
        return None
        if orientation == Qt.Orientation.Vertical:
            return None

    def get_headers(self):
        for i in range(self.columnCount(0)):
            yield HEADERS[i].capitalize()

    def get_transactions(self):
        """ count transaction number """
        return len(set(i.transaction for i in self._data))

    def get_pkgs_count(self):
        """ count packages """
        return len(set(i.package for i in self._data))


############### GUI ###############


class MainProxyModel(QSortFilterProxyModel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filters = {}

    def setFilterByColumn(self, regex: str, column: int):
        self.filters = {}
        if regex:
            self.filters[column] = regex.lower()
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        """manual filter on some colums"""
        for column, regex in self.filters.items():
            if regex == "":
                break
            index = self.sourceModel().index(source_row, column, source_parent)
            if not index.isValid():
                return False
            if text := str(self.sourceModel().data(index, Qt.ItemDataRole.DisplayRole)):
                if regex not in text.lower():
                    return False
            else:
                return False
        return True


class ToolProxyModel(QSortFilterProxyModel):
    """tool to inject one colums in small widgets (combo, autocompletion, ...)"""

    def __init__(self, column: int = 0, duplicate=True, miniLong=3):
        super().__init__()
        self._column = 0
        # TODO normalement pour ces 2 attributs suivant: setter/refresh comme self.column
        self.group = None if duplicate else set()
        self.minilong = miniLong - 1
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.column = column
        self.setDynamicSortFilter(True)

    def columnCount(self, parent=...) -> int:
        return 1

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        index = self.sourceModel().index(source_row, self.column, source_parent)
        data = str(self.sourceModel().data(index, Qt.ItemDataRole.DisplayRole))
        # règle métier, normalement méthode
        result = len(data) > self.minilong
        if result and self.group is not None:
            # valeurs unique
            data = data.casefold()
            if data in self.group:
                return False
            self.group.add(data)
        return result

    def filterAcceptsColumn(self, source_column: int, source_parent: QModelIndex) -> bool:
        """accept only one column"""
        if self.group:
            self.group.clear()
        return source_column == self.column

    @property
    def column(self):
        """get one column from model"""
        return self._column

    @column.setter
    def column(self, value: int):
        self._column = value
        self._refresh()

    def _refresh(self):
        """setter changed : view refresh"""
        self.beginResetModel()
        self.layoutChanged.emit()
        self.endResetModel()
