"""
optional deps   # --asdeps
    diffuse: editor, compare merge files
    kompare: editor, compare merge files
    meld: editor, compare merge files
    code : vscode editor
    optional gvfs       
    kio-admin for `kompare`
"""
import os
from PySide6.QtCore import QProcess
from enum import Enum

class Dep(Enum):
    GVFS = "/usr/lib/gvfsd"     # sudo pacman -Sy gvfs --asdeps
    KIO = "/usr/lib/kf6/kio-admin-helper"
    NONE = ""

    def installed(self) ->bool:
        if not self.value:
            return False
        return os.path.exists(self.value)


class Worker:
    def __init__(self, name: str, dep=Dep.GVFS, option: str|None=""):
        self.exec = name
        self.dep = dep
        self.option = option if option else ""

    def available(self) -> bool:
        return os.path.exists(self.exec)

    def run(self, msg: str):
        """
        msg = /etc/pacman.conf installed as /etc/pacman.conf.pacnew
        """
        conf, pacnew = [s.strip() for s in msg.split("installed as")]
        print("run ?", conf, pacnew)
        if not os.path.exists(conf) or not os.path.exists(pacnew):
            return
        # view only or can edit
        if self.dep.installed():
            conf = f"admin://{conf}"
            pacnew = f"admin://{pacnew}"
        arguments = [conf, pacnew]
        if self.option:
            arguments.insert(0, self.option)
        print("run:", self.exec, arguments)
        QProcess().startDetached(self.exec, arguments)

    def __repr__(self) ->str:
        return f"pacnew.Worker({self.exec})"