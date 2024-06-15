#!/usr/bin/env python
import argparse
from pathlib import Path
import sys
try:
    from PySide6.QtWidgets import QApplication
except ImportError:
    print("ERROR: install pyside6 !")
    exit(13)
from PySide6.QtCore import (
    QCoreApplication,
    QLibraryInfo,
    QLocale,
    QProcess,
    QTranslator,
)
from PySide6.QtGui import (
    QIcon,
)
from .model.alpm import Parser
from .model.store import MainModel
from .ui.application import MainWindow


LOG_FILE = "/var/log/pacman.log"

runner = QProcess()
runner.start("pacman-conf")
runner.waitForFinished()
if not runner.exitCode():
    c_out = runner.readAllStandardOutput().toStdString().splitlines()
    LOG_FILE = next(filter(lambda x: x.startswith("LogFile"), c_out)).split()[-1]

parser = argparse.ArgumentParser(prog='logkonsult-gui')
parser.add_argument("-d", type=int, default = Parser.max_day, help=f"since ({Parser.max_day}) days", metavar="DAYS")
parser.add_argument("-f", type=argparse.FileType('r'), default=LOG_FILE, help=f"pacman log ({LOG_FILE})", metavar="LOGFILE")
args =parser.parse_args()
LOG_FILE = args.f.name
print(LOG_FILE)
parser = Parser(LOG_FILE)
args.d -= 1
parser.max_day = args.d if args.d > 0 else 0

items = [*parser.load()]
if not items:
    exit(1)
items.sort()
print(len(items))

class ApplicationQt(QApplication):
    def __init__(self, args, datas: list, days):
        super().__init__(args)
        self.window = MainWindow(MainModel(datas, days), log_name=LOG_FILE)
        self.setWindowIcon(QIcon(str(Path(__file__).parent / "assets/logkonsult.svg")))

        locale = QLocale()
        trans = QTranslator()
        trans.load(f"qt_{locale.bcp47Name()}", QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath))
        QCoreApplication.installTranslator(trans)  # dialog btns translate


appli = ApplicationQt(sys.argv, datas=items, days=parser.max_day)
appli.window.show()
code = appli.exec()
if code:
    print(code)
exit(code)
