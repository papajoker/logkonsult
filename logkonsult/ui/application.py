import os
from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QTableView,
    QToolBar,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import (
    Qt,
    QDate,
    QLocale,
    QModelIndex,
    QProcess,
)
from PySide6.QtGui import (
    QAction,
    QIcon,
)
from ..model.delegates import TableDelegate
from ..model.alpm import HEADERS, TimerData, PaclogWarn
from ..model.store import MainModel, ToolProxyModel, MainProxyModel
from .widgets import VLine, CalendarWidget


class MainWindow(QMainWindow):
    def __init__(self, model: MainModel, log_name: str, editor, editor_pacnew):
        super().__init__()
        self.log_name = log_name
        self.editor = editor
        self.editor_pacnew = editor_pacnew
        self.model = model
        self.setMinimumSize(620,420)
        self.statusBar()
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
        self.table.doubleClicked.connect(self.openEditor)
        self.table.setItemDelegate(TableDelegate(self.table))

        if toolbar := self.addToolBar("tools"):

            is_xfce = "xfce" in os.environ.get("XDG_CURRENT_DESKTOP").lower()

            toolbar.setFloatable(False)
            action = QAction(QIcon.fromTheme("warning"), "Warnings", self)
            if not action.icon(): action.setIcon(QIcon.fromTheme("dialog-warning"))
            if not action.icon(): action.setIcon(QIcon.fromTheme("dialog-warning-symbolic"))
            if not action.icon() and not is_xfce:
                action.setIconText("⚠")
            action.triggered.connect(self.onSelectWarning)
            toolbar.addAction(action)
            self.filter = QComboBox()
            self.filter.addItems(self.model.get_headers())
            self.filter.setToolTip("filter type")
            self.filter.currentIndexChanged.connect(self.onFiltrerChange)
            toolbar.addWidget(self.filter)
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

            toolbar.addSeparator()
            self.action_calendar = QAction(QIcon.fromTheme("calendar"), "Calendar", self)
            if not action.icon(): action.setIcon(QIcon.fromTheme("x-office-calendar"))
            if not action.icon(): action.setIcon(QIcon.fromTheme("x-office-calendar-symbolic"))
            if not self.action_calendar.icon() and not is_xfce:
                self.action_calendar.setIconText("📅")
            self.action_calendar.setCheckable(True)
            self.action_calendar.toggled.connect(self.onToggleCalendar)
            toolbar.addAction(self.action_calendar)
            action = QAction(QIcon.fromTheme("exit"), self.tr("Exit"), self)
            if not action.icon(): action.setIcon(QIcon.fromTheme("application-exit"))
            if not action.icon(): action.setIcon(QIcon.fromTheme("application-exit-symbolic"))
            if not action.icon():
                action.setIconText("X")
            action.triggered.connect(self.close)
            toolbar.addAction(action)

        layout.addWidget(self.table)
        self.dock = QToolBar("calendar", self)
        self.dock.setAllowedAreas(Qt.ToolBarArea.BottomToolBarArea)
        self.dock.setFloatable(False)
        self.dock.setMovable(False)
        self.calendar = CalendarWidget(TimerData(self.model._data), self.dock)
        self.calendar.onSelected.connect(self.onCalendarSelect)
        self.calendar.onEnter.connect(self.onCalendarEnter)
        self.dock.setVisible(False)
        self.dock.addWidget(self.calendar)
        self.addToolBar(Qt.ToolBarArea.BottomToolBarArea, self.dock)

        #self.onSelectWarning()
        msg = QLocale.system().toString(QDate.currentDate(), format=QLocale.FormatType.ShortFormat)
        self.filter.setCurrentIndex(0)
        self.search.setText(msg)
        self.init_status_bar()

    def init_status_bar(self):
        count = self.model.get_transactions()
        self.setWindowTitle(f"{self.log_name} ({count})")
        bar = self.statusBar()
        bar.showMessage(f" {count} transactions")
        bar.addPermanentWidget(VLine())
        status = QLabel(str(self.model.get_pkgs_count()))
        status.setToolTip("Packages")
        bar.addPermanentWidget(status)
        bar.addPermanentWidget(VLine())
        status = QLabel(str(count))
        status.setToolTip("Transactions")
        bar.addPermanentWidget(status)
        bar.addPermanentWidget(VLine())
        status = QLabel(str(self.model.days+1))
        status.setToolTip("Days")
        bar.addPermanentWidget(status)

    def onFilter(self, text):
        col = 0
        if isinstance(self.search.completer().model(), ToolProxyModel):
            col = self.search.completer().model().column
        if isinstance(self.table.model(), MainProxyModel):
            self.table.model().setFilterByColumn(text, col)

    def onFiltrerChange(self, index):
        self.table.setColumnHidden(3, False)
        if isinstance(self.search.completer().model(), ToolProxyModel):
            self.search.completer().model().column = index
            if isinstance(self.table.model(), MainProxyModel):
                self.table.model().setFilterByColumn("", 0)
        self.search.setText("")
        sender = self.sender()
        if isinstance(sender, QComboBox):
            #self.search.setToolTip(f"{sender.currentText()} filter")
            self.search.setPlaceholderText(f"{sender.currentText()} entry")

    def onToggleCalendar(self, state:bool):
        self.dock.setVisible(state)
        self.action_calendar.setToolTip( f"{'hide' if state else 'show'} calendar")

    def onCalendarSelect(self, date: QDate, count: int):
        msg = QLocale.system().toString(date, format=QLocale.FormatType.ShortFormat)
        self.statusBar().showMessage(f"{msg} : {count} entr{'ies' if count > 1 else 'y'}", 5000)

    def onCalendarEnter(self, date: QDate, count: int):
        msg = QLocale.system().toString(date, format=QLocale.FormatType.ShortFormat)
        self.statusBar().showMessage(f"{msg} filter : {count} entr{'ies' if count > 1 else 'y'}", 5000)
        self.filter.setCurrentIndex(0)
        self.search.setText(msg)

    def onSelectWarning(self):
        self.filter.setCurrentIndex(1)
        self.table.setColumnHidden(3, True)
        self.search.setText("warning")

    def onCurrentIndexChanged(self, index: QModelIndex):
        self.statusBar().showMessage(index.data(Qt.ItemDataRole.StatusTipRole))

    def openEditor(self, index: QModelIndex):
        """load logfile in editor at line X"""
        entry = index.data(Qt.ItemDataRole.UserRole + 1)
        print(entry)

        if self.editor_pacnew :
            if isinstance(entry, PaclogWarn) and entry.is_pacnew() and not entry.is_fixed():
                self.editor_pacnew.run(entry.message)
                return

        if self.editor:
            print("run:", self.editor[0], self.editor[1].format(self.log_name, entry.line).split())
            QProcess().startDetached(
                self.editor[0],
                self.editor[1].format(self.log_name, entry.line).split()
            )
