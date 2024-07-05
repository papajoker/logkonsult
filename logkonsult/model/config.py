import argparse
from .pacnew import Dep, Worker
from pathlib import Path
import os
import tomllib
from .. import __version__

#TODO use also ~/.config/logkonsult.conf for editor and diff

APP_NAME = "logkonsult-gui"
max_day = 120

bin_dir = "/usr/bin/"
_editors = {
    f"{bin_dir}kate": "{0} --line {1}",
    f"{bin_dir}geany": "-s {0} --line {1}",
    f"{bin_dir}gedit": "{0} +{1}",
    f"{bin_dir}gnome-text-editor": "{0} +{1}",
    f"{bin_dir}mousepad": "{0} -l {1}",
    f"{bin_dir}pluma": "{0} +{1}",
    f"{bin_dir}code": "-g {0}:{1}",
    f"{bin_dir}zeditor": "{0}:{1}",
}

_workers = {
    f"{bin_dir}meld": (Dep.GVFS, None),
    f"{bin_dir}diffuse": (Dep.NONE, None),
    f"{bin_dir}kompare": ( Dep.NONE, None),    # bad : qt5 and admin ptotocol
    f"{bin_dir}code": (Dep.NONE, "-d"),    # read only
    f"{bin_dir}kate": (Dep.NONE, None),   # test for Dep.KIO BUT not usefull to use kio_admin
    f"{bin_dir}tkdiff": (Dep.NONE, None),
}

def format_exec(exec) -> str:
    if exec and not exec.startswith("/"):
        exec = bin_dir + exec
    return exec

editor = None
worker = None

conf_file = Path(f"~/.config/{APP_NAME.split('-', maxsplit=1)[0]}.conf").expanduser()
print("#read config file", conf_file, "\n")
if conf_file.exists():
    with open(conf_file, "rb") as f:
        data = tomllib.load(f)
        max_day = data.get("days",max_day)
        editor_name = format_exec(data.get("editor"))
        try:
            editor = (editor_name,_editors[editor_name])
        except KeyError:
            editor = None
        diff_name = format_exec(data.get("diff"))
        try:
            worker = Worker(diff_name, *_workers[diff_name])
        except KeyError:
            worker = None

if not editor:
    # search installed  for default
    try:
        editor = next(e for e in _editors.items() if os.path.exists(e[0]))
    except StopIteration:
        editor = ("?","")

if not worker:
    # search installed for default
    try:
        w = next(w for w in _workers if os.path.exists(w))
        worker = Worker(w, *_workers[w])
    except StopIteration:
        worker = None

def prune_type(x):
    x = int(x)
    if x < 1:
        raise argparse.ArgumentTypeError("Minimum value is one day")
    return x

def diff_type(diff):
    if not diff:
        return ""
    diff = format_exec(diff)
    if not _workers.get(diff):
        raise argparse.ArgumentTypeError("Editor not available")
    return diff

def read_conf(args_script, log_file: str):

    parser = argparse.ArgumentParser(prog=APP_NAME, epilog = f"Version: {__version__}")
    parser.add_argument("-d", type=int, default = max_day, help=f"since ({max_day}) days", metavar="DAYS")
    parser.add_argument("-f", type=argparse.FileType('r'), default=log_file, help=f"pacman log ({log_file})", metavar="LOGFILE")
    if editor:
        parser.add_argument("-e", type=str, default=editor[0], help=f"{editor[0]} for view log", metavar="EDITOR")
    if isinstance(worker, Worker):
        parser.add_argument("-diff", type=diff_type, default=worker.exec, help=f"{worker.exec} for view differences", metavar="EDITOR")
    parser.add_argument("--prune", type=prune_type, help="delete old entries, except X days and remove `SCRIPTLET` lines", metavar="KEEPDAYS")
    args = parser.parse_args(args_script)

    args.e = format_exec(args.e)
    try:
        args.e = (args.e,_editors[args.e])
    except (KeyError, AttributeError):
        args.e = None

    try:
        args.diff =  Worker(args.diff, *_workers[args.diff])
    except (KeyError, AttributeError):
        args.diff = None

    # print(args)
    return args
