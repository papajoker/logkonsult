import datetime
from PySide6.QtWidgets import (
    QStyleOptionViewItem,
    QStyledItemDelegate,
)
from PySide6.QtCore import (
    Qt,
    QDateTime,
    QModelIndex,
    QPoint,
    QRect,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QPainter,
    QPalette,
    QPen,
)
from model.alpm import HEADERS, Verbs



class TableDelegate(QStyledItemDelegate):
    #WARN_COLOR = QColor(200, 90, 90, 200)
    WARN_COLOR = QColor("orange")
    transaction = 0

    def __init__(self, parent):
        super().__init__(parent)
        self._hfont = -1
        self.default_size = 9

    def initStyleOption(self, option: QStyleOptionViewItem, index):
        super().initStyleOption(option, index)
        self.default_size = option.font.pointSize()
        if self._hfont < self.default_size:
            self._hfont = self.default_size
        option.font.setPointSize(self._hfont)
        option.displayAlignment = option.displayAlignment | Qt.AlignLeft

        '''if HEADERS[index.column()] == "date":
            d = index.data(Qt.ItemDataRole.UserRole + 1).date
            print(d, type(d))
            #d = QDateTime.fromSecsSinceEpoch(d.timestamp())
            d = QDateTime.fromSecsSinceEpoch(round(d.timestamp()))
            d.setTimeSpec(Qt.TimeSpec.LocalTime)
            print(d.toString(Qt.ISODate))
            option.text = f" {d.toString(Qt.TextDate)}"
            
            """transaction = index.data(Qt.ItemDataRole.UserRole + 1).transaction
            if transaction % 2 == 0:
                option.backgroundBrush = QBrush(QColor("gray"))"""
        '''

        if HEADERS[index.column()] == "action":
            if index.data() == Verbs.WARNING.name.lower():
                option.palette.setBrush(QPalette.Text, self.WARN_COLOR)
            option.displayAlignment = option.displayAlignment | Qt.AlignCenter
            option.text = index.data(Qt.ItemDataRole.UserRole)
        else:
            option.text = f" {option.text}"

    def paint(self, painter: QPainter, option: 'QStyleOptionViewItem', index: QModelIndex) -> None:
        super().paint(painter, option, index)
        if HEADERS[index.column()] == "date":
            color = index.data(Qt.ItemDataRole.UserRole + 1).color
            painter.save()
            pen = QPen(color)
            pen.setWidth(3)
            qr = QRect(option.rect)
            #print(option.rect)
            #qr.setWidth(pen.width())
            #pen.setColor(QColor(f"#EB51{transaction}"))
            #pen.setColor(QColor(random.randint(0, 255),random.randint(0, 255),random.randint(0, 255),random.randint(100, 255)))

            painter.setPen(pen)
            #painter.drawRect(qr)
            # QRect(400, 60, 306, 29) x,y, w, h

            painter.drawLine(
                QPoint(qr.x(), qr.y() + 2),
                QPoint(qr.x(), qr.y() + qr.height()-2)
            )
            painter.restore()

    def onZoom(self, direction: int):
        """chnage font size with CTRL+ and CTRL-"""
        size = self._hfont
        value = size - 1 if direction < 0 else size + 1
        self._hfont = self.default_size if value < self.default_size else value
        if self._hfont != size:
            self.sizeHintChanged.emit(QModelIndex())  # view refresh
