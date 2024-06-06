import os
from PySide6.QtWidgets import (
    QCalendarWidget,
    QComboBox,
    QCompleter,
    QDialogButtonBox,
    QHeaderView,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QSizePolicy,
    QTableView,
    QToolBar,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import (
    Qt,
    QAbstractTableModel,
    QDate,
    QProcess,
    QSortFilterProxyModel,
)
from PySide6.QtGui import (
    QAction,
    QIcon,
)
from logkonsult.model.delegates import TableDelegate
from logkonsult.model.alpm import HEADERS, TimerData
from logkonsult.model.store import ToolProxyModel, MainProxyModel

class MainWindow(QMainWindow):
    def __init__(self, model: QAbstractTableModel):
        super().__init__()
        self.model = model
        self.setWindowTitle(f"/var/log/pacman.log ({self.model.get_transactions()})")
        self.resize(820, 380)
        self.statusBar()
        #self.edits = {}
        self.init_ui()

    def init_ui(self):
        self.setCentralWidget(QWidget(parent=self))
        layout = QVBoxLayout(self.centralWidget())

        self.table = QTableView()
        self.filterModel = MainProxyModel()
        self.filterModel.setSourceModel(self.model)
        self.filterModel.setFilterKeyColumn(0)
        self.table.setModel(self.filterModel)

        if header := self.table.horizontalHeader():
            header.setSectionResizeMode(
                QHeaderView.ResizeMode.ResizeToContents # Stretch
            )
            header.setSectionResizeMode(
                QHeaderView.ResizeMode.Interactive # Stretch
            )
            header.setSectionResizeMode(len(HEADERS)-1, QHeaderView.ResizeMode.Stretch)

        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.clicked.connect(self.onCurrentIndexChanged)
        self.table.doubleClicked.connect(self.onDoubleClicked)
        self.table.setItemDelegate(TableDelegate(self.table))

        if toolbar := self.addToolBar("tools"):

            toolbar.setFloatable(False)
            self.search = QLineEdit()
            self.search.setPlaceholderText("...")
            self.search.setToolTip("filter")
            self.search.textChanged.connect(self.onFilter)
            if completer := QCompleter():
                modelproxy = ToolProxyModel(duplicate=False)
                modelproxy.setSourceModel(self.model)
                completer.setCaseSensitivity(Qt.CaseInsensitive)
                completer.setModel(modelproxy)
                completer.setModelSorting(QCompleter.ModelSorting.CaseInsensitivelySortedModel)
                self.search.setCompleter(completer)
            toolbar.addWidget(self.search)
            self.filter = QComboBox()
            self.filter.addItems(self.model.get_headers())
            self.filter.setToolTip("filter type")
            self.filter.currentIndexChanged.connect(self.onFiltrerChange)
            toolbar.addWidget(self.filter)

            toolbar.addSeparator()
            action = QAction(QIcon.fromTheme("warning"), "Warnings", self)
            action.triggered.connect(self.onSelectWarning)
            toolbar.addAction(action)
            action = QAction(QIcon.fromTheme("exit"), self.tr("Exit"), self)
            action.triggered.connect(self.close)
            toolbar.addAction(action)

        layout.addWidget(self.table)
        calendar = QCalendarWidget(self.centralWidget())
        self.init_calendar(calendar)
        layout.addWidget(calendar)
        #layout.addLayout(layoutBtn)

        self.onSelectWarning()
        self.statusBar().showMessage(f" {self.model.get_transactions()} transactions")

    def init_calendar(self, calendar):
        times = TimerData(self.model._data)
        maxi = QDate.fromString(list(times.datas.keys())[0], "yyyy-MM-dd")
        calendar.setMaximumDate(maxi)
        mini = QDate.fromString(list(times.datas.keys())[-1], "yyyy-MM-dd")
        calendar.setDateRange(mini, maxi)

    def onFilter(self, text):
        col = 0
        if isinstance(self.search.completer().model(), ToolProxyModel):
            col = self.search.completer().model().column
        if isinstance(self.table.model(), MainProxyModel):
            self.table.model().setFilterByColumn(text, col)

    def onFiltrerChange(self, index):
        if isinstance(self.search.completer().model(), ToolProxyModel):
            self.search.completer().model().column = index
            if isinstance(self.table.model(), MainProxyModel):
                self.table.model().setFilterByColumn("", 0)
        self.search.setText("")
        sender = self.sender()
        if isinstance(sender, QComboBox):
            #self.search.setToolTip(f"{sender.currentText()} filter")
            self.search.setPlaceholderText(f"{sender.currentText()} entry")

    '''def onCurrentRowChanged(self, index):
        """ lier le tableau au formulaire """
        if isinstance(self.table.model(), QSortFilterProxyModel):
            # convertir la ligne car on utilise un filtre
            index = self.table.model().mapToSource(index)
        self.statusBar().showMessage(f"ligne {index.row()}")
        self.mapper.setCurrentModelIndex(index)   # sans filtre on pouvais connecter directement cette méthode !
    '''

    def onSelectWarning(self):
        self.filter.setCurrentIndex(1)
        self.search.setText("warning")

    def onCurrentIndexChanged(self, index):
        self.statusBar().showMessage(index.data(Qt.ItemDataRole.StatusTipRole))

    def onDoubleClicked(self, index):
        entry = index.data(Qt.ItemDataRole.UserRole + 1)
        print(entry)
        if not os.path.exists("/usr/bin/kate"):
            return
        print(f'kate "/var/log/pacman.log" --line {entry.line} ...')
        process = QProcess()
        process.startDetached("/usr/bin/kate", ["/var/log/pacman.log", "--line", f"{entry.line}"])


    def closeEvent(self, event):
        event.accept()
