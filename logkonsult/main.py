#!/usr/bin/env python
import sys
try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import (
        QCoreApplication,
        QLibraryInfo,
        QLocale,
        QTranslator,
    )
    from PySide6.QtGui import (
        QIcon,
    )
except ImportError:
    print("ERROR: install pyside 6 !")
    exit(13)
from model.alpm import Parser
from model.store import MainModel
import application

LOG_FILE = "/var/log/pacman.log"


parser = Parser(LOG_FILE)
items = [*parser.load()]
if not items:
    exit(1)
items.sort()
print(len(items))

class ApplicationQt(QApplication):
    def __init__(self, args, datas: list):
        super().__init__(args)
        self.window = application.MainWindow(MainModel(datas))
        self.setWindowIcon(QIcon(str("logkonsult.svg")))

        locale = QLocale()
        #print(locale.name(), locale.bcp47Name(), locale)
        trans = QTranslator()
        trans.load(f"qt_{locale.bcp47Name()}", QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath))
        QCoreApplication.installTranslator(trans)  # dialog btns translate


appli = ApplicationQt(sys.argv, datas=items)
appli.window.show()
code = appli.exec()
if code:
    print(code)
exit(code)
