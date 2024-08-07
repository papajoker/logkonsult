from collections import defaultdict
import datetime
from enum import Enum
from pathlib import Path
import shutil
import sys
from PySide6.QtCore import QDateTime, QLocale


class Verbs(Enum):
    """pacman transaction type"""

    # NONE = 0    # TODO remove
    # TRANSACTION = 1
    WARNING = 0
    INSTALLED = 1
    REMOVED = 2
    REINSTALLED = 3
    UPGRADED = 4

    @property
    def txt(self):
        name = self.name.lower()
        if self == Verbs.WARNING:
            return f"{name}:"
        return name

    @classmethod
    def values(cls):
        return [v.txt for v in cls]


HEADERS = ("date", "action", "package", "version", "message")
ICO_ACTIONS = ("⚠", ">", "<", "≫", "🗘")


class Paclog:
    """
    entry in log file
    """
    __slots__ = ("date", "package", "version", "action", "transaction", "line", "color", "qdate", "datelog", "installed")

    def __init__(self, datelog: datetime.datetime, pkg: str, version: str, verb: Verbs, transaction:int, line:int, installed=True):
        self.datelog = datelog
        self.package = pkg
        self.version = version
        self.action = verb
        self.transaction = transaction
        self.color = None
        self.line = line
        self.qdate = QDateTime.fromSecsSinceEpoch(round(datelog.timestamp()))
        self.date = QLocale.system().toString(self.qdate, format=QLocale.FormatType.ShortFormat)
        self.installed = installed

    def __getitem__(self, key: int):
        """ access as array"""
        name = HEADERS[key]
        match name:
            case "action":
                value = self.__getattribute__(name).name.lower()
            # case "date": value = f"{self.__getattribute__(name):%Y-%m-%d}"
            case _ :
                try:
                    value = self.__getattribute__(name)
                except AttributeError:
                    value = ""
        return value

    def __lt__(self, other):
        """ first transaction reversed, date """
        if self.transaction == other.transaction:
            return self.datelog > other.datelog
        return self.transaction > other.transaction

    def get_ico(self) -> str:
        """ action to icon """
        return ICO_ACTIONS[self.action.value]

    def __str__(self):
        return f"[{self.datelog}] {self.action.name:12} : {self.package:28} {self.version} ({self.transaction})"


'''
search `alpm_logaction` in https://gitlab.archlinux.org/pacman/pacman/-/blob/master/lib/libalpm/add.c
'''
class PaclogWarn(Paclog):
    """
    entry with warning in log file
    """
    __slots__ = ("message",)

    def __init__(self, datelog, msg: str, transaction:int, line:int):
        super().__init__(datelog, pkg="", version="", verb=Verbs.WARNING, transaction=transaction, line=line)
        # [ALPM] warning: /etc/mkinitcpio.conf installed as /etc/mkinitcpio.conf.pacnew
        msg_parts = msg.split()
        if msg.endswith(".pacnew") and not Path(msg_parts[-1]).exists():
            msg = f"FIXED {msg}"
        elif "permissions differ" in msg:
            mode, dir_ = msg_parts[-1], Path(msg_parts[-5].removesuffix(","))
            try:
                if not dir_.exists() or mode == oct(dir_.stat().st_mode)[-3:]:
                    msg = f"FIXED {msg}"
            except PermissionError:
                pass
        self.message = msg

    def get_file(self) -> str:
        """ file in warning message"""
        if self.is_pacnew():
            return self.message.split()[0]
        elif "permissions differ" in self.message:
            return self.message.split()[-5].removesuffix(",")
        return ""

    def is_fixed(self):
        return self.message.startswith("FIXED")

    def is_pacnew(self):
        return self.message.endswith(".pacnew")

    def get_ico(self) -> str:
        """ action to icon """
        return super().get_ico() if not self.is_fixed() else "!"

    def __str__(self):
        return f"[{self.date}] {self.action.name:12} : {self.package:28} -> {self.message}"


class Parser:
    """
    read pacman.log
    """
    max_day = 90
    goods = Verbs.values()
    INIT_TRANSACTION = "[PACMAN] Running"

    def __init__(self, lfile, pkgs: list|None):
        self.logfile = lfile
        self.pkgs = pkgs if pkgs else []

    def generate_dicts(self, log_fh):
        """parse logs"""
        fields = {}
        warn = None
        transaction_count = 0
        transaction_id = 0
        line_id = 0
        for line in log_fh:      # cant use enumerate -> old version : warning on 2..3 lines
            line_id += 1
            if self.INIT_TRANSACTION in line:
                transaction_count -= 1
            if "[ALPM]" in line:
                msg = line.split("] ", 2)[-1].strip()
                msgs = msg.split(" ")
                # print(msgs[0])
                if msgs[0] not in self.goods:
                    continue
                try:
                    fields = {
                        "date": line.split("] ", 1)[0][1:],
                        # "type": line.split("] ", 2)[1][1:],
                        "verb": Verbs[msgs[0].upper().removesuffix(":")],
                        "pkg": msgs[1],
                        "ver": msgs[2:],
                        "msg": line.split("] ", 2)[-1].strip(),
                    }
                except ValueError:
                    continue

                # [2024-01-30T01:04:53+0100]    '%Y-%m-%dT%H:%M:%S%z'
                # [2024-01-30 01:04]  old    '%Y-%m-%d %H:%M'
                try:
                    logdate = datetime.datetime.strptime(fields["date"], "%Y-%m-%dT%H:%M:%S%z")
                    diffdate = datetime.datetime.now(datetime.timezone.utc) - logdate
                except ValueError:
                    continue
                # only last days
                if diffdate.days > self.max_day:
                    continue
                fields["date"] = logdate

                if fields["verb"] == Verbs.WARNING:
                    fields["msg"] = fields["msg"][9:]
                    if "directory permissions differ" in fields["msg"]:
                        if "," not in fields["msg"]:    # OLD version, msg in next line !
                            fields["msg"] = fields["msg"] + ", " + next(log_fh).rstrip()
                            line_id += 1
                        fields["msg"] = fields["msg"]
                    if transaction_id != transaction_count:
                        transaction_id += 1
                        transaction_count = transaction_id
                    warn = PaclogWarn(
                        datelog=fields["date"],
                        msg=fields["msg"],
                        transaction=transaction_id,
                        line = line_id,
                    )
                    yield warn
                    continue

                if fields["verb"] == Verbs.UPGRADED:
                    fields["ver"] = fields["ver"][2][:-1]
                if fields["verb"] == Verbs.INSTALLED:  # in (Verbs.INSTALLED, Verbs.REMOVED):
                    ver = fields["ver"][0]
                    if ver:
                        fields["ver"] = ver[1:-1]
                if fields["verb"] == Verbs.REMOVED:
                    fields["ver"] = ""
                if fields["ver"] and isinstance(fields["ver"], list):
                    fields["ver"] = fields["ver"][0][1:-1]

                if warn and fields["pkg"]:
                    # no sens with yield, too late -> console -> warn is displayed
                    # FIXME  if 2 consecutive errors -> no package
                    warn.package = fields["pkg"]
                    warn.installed = fields["pkg"] in self.pkgs if self.pkgs else True
                    warn = None

                if transaction_id != transaction_count:
                    transaction_id += 1
                    transaction_count = transaction_id
                yield Paclog(
                    datelog=fields["date"],
                    verb=fields["verb"],
                    version=fields["ver"],
                    pkg=fields["pkg"],
                    transaction=transaction_id,
                    line = line_id,
                    installed = fields["pkg"] in self.pkgs if self.pkgs else True
                )

    def load(self):
        """load pacman log"""
        with open(self.logfile) as fin:
            yield from self.generate_dicts(fin)


class TimerData:
    """ model for calendar, available dates """
    def __init__(self, logs: list[Paclog]):
        self.logs = logs
        self.datas = defaultdict(lambda: [0,0,0])
        for log, warm in ((l.qdate.date(), isinstance(l, PaclogWarn) and not l.message.startswith("FIXED")) for l in logs if isinstance(l, Paclog)):
            self.datas[log][0] += 1
            if warm :
                self.datas[log][2] += 1
        self.maxi : int = max(v[0] for v in self.datas.values())
        for i, val in self.datas.items():
            count, pourcent, warm = val
            pourcent = round(count / self.maxi * 100)
            self.datas[i] = (count, (pourcent // 5 ) * 5 if pourcent < 100 else 100, warm)


def prune_log(logfile: str, keep_days=360) -> int:
    """purge pacman log of old entries"""
    try:
        if not shutil.copyfile(logfile, f"{logfile}~"):
            return 3
    except PermissionError as err:
        print(err, file=sys.stderr)
        return err.errno
    good = False
    today = datetime.date.today()
    with open(f"{logfile}~", 'r') as f_in:
        with open(f"{logfile}.clean", mode='w') as f_out:    # TODO remove .clean
            for line in f_in:
                if "[ALPM-SCRIPTLET]" in line:
                    continue
                if good:
                    f_out.write(line)
                    continue
                if not line.startswith("["):
                    continue
                try:
                    line_date = datetime.datetime.strptime(line[1:11], "%Y-%m-%d").date()
                except ValueError:
                    continue
                if (today - line_date).days < keep_days:
                    good = True
                    f_out.write(line)
    print("Not implemented,", "result in temporary file:", f"{logfile}.clean")
    return 0


if __name__ == "__main__":
    for v in Verbs:
        print(f"{v:20}  {v.txt}")
    print()
    print(Verbs(1))
    print(Verbs["INSTALLED"])

    LOG_FILE = "/var/log/pacman.log"
    parser = Parser(LOG_FILE)
    '''
    items = parser.load()
    for item in items:
        print(item)
    print()
    '''
    items = [*parser.load()]
    items.sort()
    for item in items:
        print(item)

    print()
    print("transactions:", len([i.transaction for i in items]))
    print("transactions:", len(set(i.transaction for i in items)))

    ts = TimerData(items)
    for t in ts.datas.items():
        print(t)
    print()
    print(len(ts.datas), "days")
    print(ts.count(), "packages")
    print("min/max", ts.min_max())
