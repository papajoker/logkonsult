#!/usr/bin/env python

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
from .model.alpm import Parser, prune_log
from .model.store import MainModel
from .model.config import read_conf
from .ui.application import MainWindow


LOG_FILE = "/var/log/pacman.log"

runner = QProcess()
runner.start("/usr/bin/pacman-conf")
runner.waitForFinished()
if not runner.exitCode():
    c_out = runner.readAllStandardOutput().toStdString().splitlines()
    LOG_FILE = next(filter(lambda x: x.startswith("LogFile"), c_out)).split()[-1]

runner.startCommand("/usr/bin/pacman -Qq")
runner.waitForFinished()
if not runner.exitCode():
    pkgs = runner.readAllStandardOutput().toStdString().splitlines()

conf = read_conf(
    sys.argv[1:],
    LOG_FILE
)

LOG_FILE = conf.f.name
print(LOG_FILE)

if conf.prune:
    exit(prune_log(LOG_FILE, conf.prune))

parser = Parser(LOG_FILE, pkgs)
conf.d -= 1
parser.max_day = conf.d if conf.d > 0 else 0

items = [*parser.load()]
if not items:
    exit(1)
items.sort()
print(len(items))

class ApplicationQt(QApplication):
    def __init__(self, args, datas: list, days):
        super().__init__(args)
        self.window = MainWindow(
            MainModel(datas, days),
            log_name=LOG_FILE,
            editor= conf.e,
            editor_pacnew = conf.diff
        )
        self.setWindowIcon(QIcon(str(Path(__file__).parent / "assets/logkonsult.svg")))

        locale = QLocale()
        trans = QTranslator()
        trans.load(f"qt_{locale.bcp47Name()}", QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath))
        QCoreApplication.installTranslator(trans)  # dialog btns translate


appli = ApplicationQt(sys.argv, datas=items, days=parser.max_day)
appli.window.show()
code = appli.exec()
exit(code)
