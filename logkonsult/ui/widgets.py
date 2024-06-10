from PySide6.QtCore import (
    Qt,
    QAbstractTableModel,
    QDate,
    QEvent,
    QProcess,
    Signal,
    QSortFilterProxyModel,
)
from PySide6.QtWidgets import (
    QCalendarWidget,
    QFrame,
    QTableView,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QPainter,
    QPalette,
    QPen,
    QTextCharFormat,
)
from ..model.alpm import TimerData


class VLine(QFrame):
    # a simple VLine, like the one you get from designer
    def __init__(self):
        super(VLine, self).__init__()
        self.setFrameShape(QFrame.Shape.VLine)
        self.setFrameShadow(QFrame.Shadow.Sunken) 


class CalendarWidget(QCalendarWidget):

    onSelected = Signal(object, int)
    onEnter = Signal(object, int)

    def __init__(self, dates:TimerData, parent=None):
        super().__init__(parent, gridVisible=False,
            horizontalHeaderFormat=QCalendarWidget.SingleLetterDayNames,
            verticalHeaderFormat=QCalendarWidget.NoVerticalHeader,
            navigationBarVisible=True,
            dateEditEnabled=True)
        self.setWeekdayTextFormat(Qt.DayOfWeek.Saturday, self.headerTextFormat())
        self.setWeekdayTextFormat(Qt.DayOfWeek.Sunday, self.headerTextFormat())
        self.dates = dates
        self.setEnabled(True)
        self.clicked.connect(self.onClick)
        self.activated.connect(self.onDoubleClicked)

        self.table_view = self.findChild(QTableView, "qt_calendar_calendarview")
        self.table_view.viewport().installEventFilter(self)
        self.setFirstDayOfWeek(Qt.Monday)

        self.setDateRange(
            list(self.dates.datas.keys())[0],
            list(self.dates.datas.keys())[-1]
        )

    def referenceDate(self):
        refDay = 1
        while refDay <= 31:
            refDate = QDate(self.yearShown(), self.monthShown(), refDay)
            if refDate.isValid(): return refDate
            refDay += 1
        return QDate()

    def columnForDayOfWeek(self, day):
        m_firstColumn = 1 if self.verticalHeaderFormat() != QCalendarWidget.NoVerticalHeader else 0
        if day < 1 or day > 7: return -1
        column = day - int(self.firstDayOfWeek().value)
        if column < 0:
            column += 7
        return column + m_firstColumn

    def columnForFirstOfMonth(self, date):
        return (self.columnForDayOfWeek(date.dayOfWeek()) - (date.day() % 7) + 8) % 7

    def dateForCell(self, row, column):
        m_firstRow = 1 if self.horizontalHeaderFormat() != QCalendarWidget.NoHorizontalHeader else 0
        m_firstColumn = 1 if self.verticalHeaderFormat() != QCalendarWidget.NoVerticalHeader else 0
        rowCount = 6
        columnCount = 7
        if row < m_firstRow or row > (m_firstRow + rowCount -1) or column < m_firstColumn or column > (m_firstColumn + columnCount -1):
            return QDate()
        refDate = self.referenceDate()
        if not refDate.isValid():
            return QDate()
        columnForFirstOfShownMonth = self.columnForFirstOfMonth(refDate)
        if (columnForFirstOfShownMonth - m_firstColumn) < 1:
            row -= 1
        requestedDay = 7*(row - m_firstRow) +  column  - columnForFirstOfShownMonth - refDate.day() + 1
        return refDate.addDays(requestedDay)

    def eventFilter(self, obj, event):
        """ select only dates not empty """
        if event.type() ==QEvent.MouseButtonRelease and obj is self.table_view.viewport():
            ix = self.table_view.indexAt(event.position().toPoint())
            date = self.dateForCell(ix.row(), ix.column())
            if not self.dates.datas.get(date):
                return True
        return super().eventFilter(obj, event)

    def paintCell(self, painter, rect, date):
        if values := self.dates.datas.get(date):
            val, pourcent = values
            color = QPalette().color(QPalette.ColorRole.Text)
            painter.setPen(QPen(Qt.transparent))
            colorb = QPalette().color(QPalette.ColorRole.Highlight)
            colorb.setAlpha((pourcent*2)+55)
            brush = QBrush(colorb)
            brush.setStyle(Qt.Dense4Pattern)
            painter.setBrush(brush)
            painter.drawRect(rect)
        else:
            color = QPalette().color(QPalette.ColorGroup.Disabled, QPalette.ColorRole.PlaceholderText)
        painter.setPen(QPen(color))
        painter.drawText(rect, Qt.AlignHCenter | Qt.AlignVCenter, date.day())

    def onClick(self, date):
        count = self.dates.datas.get(date)[0]
        print(self.dates.datas.get(date))
        self.onSelected.emit(date, count)

    def onDoubleClicked(self, date):
        count = self.dates.datas.get(date)[0]
        self.onEnter.emit(date, count)
