from collections import defaultdict
import datetime
from enum import Enum
from pathlib import Path


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


#TODO Qdate ? 
# use Qdate in Paclog ? to test in new branch
#   best for less conversions in view ?
#   best for filter date by locale format 

class Paclog:
    """
    entry in log file
    """
    __slots__ = ("date", "package", "version", "action", "transaction", "line", "color")

    def __init__(self, ldate, pkg: str, version: str, verb: Verbs, transaction:int, line:int):
        self.date = ldate
        self.package = pkg
        self.version = version
        self.action = verb
        self.transaction = transaction
        self.color = None
        self.line = line

    def __getitem__(self, key: int):
        """ access as array"""
        name = HEADERS[key]
        match name:
            case "action":
                value = self.__getattribute__(name).name.lower()
            case "date":
                value = f"{self.__getattribute__(name):%Y-%m-%d}"
            case _ :
                try:
                    value = self.__getattribute__(name)
                except AttributeError:
                    value = ""
        return value

    def __lt__(self, other):
        """ first transaction reversed, date """
        if self.transaction == other.transaction:
            return self.date > other.date
        return self.transaction > other.transaction


    def get_ico(self) -> str:
        """ action ti icon """
        return ICO_ACTIONS[self.action.value]

    def __str__(self):
        return f"[{self.date}] {self.action.name:12} : {self.package:28} {self.version} ({self.transaction})"


class PaclogWarn(Paclog):
    """
    entry with warning in log file
    """
    __slots__ = ("message",)

    def __init__(self, ldate, msg: str, transaction:int, line:int):
        super().__init__(ldate, pkg="", version="", verb=Verbs.WARNING, transaction=transaction, line=line)
        if msg.endswith(".pacnew") and not Path(msg.split()[-1]).exists():
            msg = f"FIXED {msg}"
        self.message = msg

    def __str__(self):
        return f"[{self.date}] {self.action.name:12} : {self.package:28} -> {self.message}"


class Parser:
    """
    read pacman.log
    """
    max_day = 60
    goods = Verbs.values()
    INIT_TRANSACTION = "[PACMAN] Running"

    def __init__(self, lfile):
        self.logfile = lfile

    def generate_dicts(self, log_fh):
        """parse logs"""
        fields = {}
        warn = None
        transaction_count = 0
        transaction_id = 0
        for line_id, line in enumerate(log_fh, start=1):
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

                # print(fields)
                # print(msgs)
                # print()

                if fields["verb"] == Verbs.WARNING:
                    # fields['verb'] = fields['verb'][:-1]
                    fields["msg"] = fields["msg"][9:]
                    # fields['pkg'] = '' # old_pkg
                    # fields['ver'] = ''
                    if "directory permissions differ" in fields["msg"]:
                        fields["msg"] = fields["msg"] + " " + next(log_fh).rstrip()
                    if transaction_id != transaction_count:
                        transaction_id += 1
                        transaction_count = transaction_id
                    warn = PaclogWarn(
                        ldate=fields["date"],
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
                    # FIXME ? no sens with yield, too late -> console -> warn is displayed
                    warn.package = fields["pkg"]
                    warn = None

                if transaction_id != transaction_count:
                    transaction_id += 1
                    transaction_count = transaction_id
                yield Paclog(
                    ldate=fields["date"],
                    verb=fields["verb"],
                    version=fields["ver"],
                    pkg=fields["pkg"],
                    transaction=transaction_id,
                    line = line_id,
                )

    def load(self):
        """load pacman log"""
        with open(self.logfile) as fin:
            yield from self.generate_dicts(fin)


class TimerData:
    def __init__(self, logs: list[Paclog]):
        self.logs = logs
        #d = defaultdict(lambda: 0)
        self.datas = defaultdict(lambda: 0)
        for log in (l.date for l in logs if isinstance(l, Paclog)):
            self.datas[str(log.date())] += 1


    def count(self) -> int:
        ret = 0
        return sum(self.datas.values())

    def min_max(self) -> tuple[int, int]:
        return min(self.datas.values()), max(self.datas.values())




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
