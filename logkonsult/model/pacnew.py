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


bin_dir = "/usr/bin/"
_workers = [
    (f"{bin_dir}meld", Dep.GVFS),
    (f"{bin_dir}diffuse", Dep.GVFS),
    (f"{bin_dir}kompare", Dep.NONE),    # bad : qt5 and admin ptotocol   
    (f"{bin_dir}code", Dep.NONE, "-d"),    # read only
    # (f"{bin_dir}kate", Dep.KIO),   # test for Dep.KIO
]


class Worker:
    def __init__(self, name: str, dep=Dep.GVFS, option: str|None=""):
        self.exec = name
        self.dep = dep
        self.option = option if option else ""

    def available(self) -> bool:
        return os.path.exists(self.exec)
    
    def run(self, pkg: str, msg: str):
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

#TODO for select diff-editor: use script arg and/or ~/.logkonsult.conf
# same for editor


try:
    worker = next(w for w in _workers if os.path.exists(w[0])) # and w[1].installed())
    worker = Worker(*worker)
    print("worker =", worker.exec)
except StopIteration:
    worker = None
