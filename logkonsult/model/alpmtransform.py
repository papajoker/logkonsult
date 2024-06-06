"""
read only [ALPM]
[2019-02-04 05:11] [PACMAN] synchronizing package lists

[2019-02-04 05:13] [ALPM] transaction started
[2019-02-04 05:13] [ALPM] removed hidapi (0.8.0rc1-3)
[2019-02-04 05:13] [ALPM] reinstalled pacman-contrib (1.1.0-1)
[2019-02-04 03:44] [ALPM] upgraded libreoffice-fresh (6.1.4-4 -> 6.1.4-5)
[2019-02-04 05:13] [ALPM] transaction completed

[2019-02-07 15:27] [PACMAN] starting full system upgrade
[2019-02-07 15:31] [ALPM] transaction started
[2019-02-07 15:31] [ALPM-SCRIPTLET] ==> Starting build: 4.19.20-1-lts

[2019-01-15 16:41] [ALPM] warning: directory permissions differ on /etc/polkit-1/
filesystem: 750  package: 755
[2014-06-28 19:36] [ALPM] warning: /etc/plymouth/plymouthd.conf saved as /etc/plymouth/plymouthd.conf.pacsave

 {Date}  {Type} {verb pkg (version"s")}
"""

import json
import datetime

good_verbs = ['transaction', 'removed', 'installed', 'reinstalled', 'upgraded', 'warning:']


class AlpmTransform:
    """
    load pacman.log
    save to pacman.json.log
    """
    logfile = "/var/log/pacman.log"
    max_day = 60

    def generate_dicts(self, log_fh):
        """parse logs"""
        currentDict = {}
        warm = None
        for line in log_fh:
            if '[ALPM]' in line:

                msg = line.split("] ", 2)[-1].strip()
                msgs = msg.split(" ")
                # print(msgs[0])
                if msgs[0] not in good_verbs:
                    continue
                currentDict = {
                    "date": line.split("] ", 1)[0][1:],
                    "type": line.split("] ", 2)[1][1:],
                    "verb": msgs[0],
                    "pkg": msgs[1],
                    "ver": msgs[2:],
                    "msg": line.split("] ", 2)[-1].strip(),
                }
                #old_pkg = currentDict['pkg']

                #[2024-01-30T01:04:53+0100]    '%Y-%m-%dT%H:%M:%S%z'
                #[2024-01-30 01:04]  old    '%Y-%m-%d %H:%M'
                try:
                    logdate = datetime.datetime.strptime(currentDict['date'], '%Y-%m-%dT%H:%M:%S%z')
                    diffdate = datetime.datetime.now(datetime.timezone.utc) - logdate
                except ValueError:
                    logdate = datetime.datetime.strptime(currentDict['date'], '%Y-%m-%d %H:%M')
                    diffdate = datetime.datetime.today() - logdate
                # only last days
                if diffdate.days > self.max_day:
                    continue
                currentDict["date"] = logdate
                

                # warning
                if msgs[0] == good_verbs[5]:
                    currentDict['verb'] = currentDict['verb'][:-1]
                    currentDict['msg'] = currentDict['msg'][9:]
                    currentDict['pkg'] = '' # old_pkg
                    currentDict['ver'] = ''
                    if 'directory permissions differ' in currentDict['msg']:
                        currentDict['msg'] = currentDict['msg'] + ' ' + next(log_fh).rstrip()
                    warm = currentDict
                    yield currentDict
                    continue

                if msgs[0] == good_verbs[4]:
                    currentDict['ver'] = currentDict['ver'][2][:-1]
                if msgs[0] == good_verbs[2] or msgs[0] == good_verbs[1]:
                    ver = currentDict['ver'][0]
                    if ver:
                        currentDict['ver'] = ver[1:-1]
                if currentDict['ver'] and isinstance(currentDict['ver'], list):
                    currentDict['ver'] = currentDict['ver'][0][1:-1]
                if msgs[0] == good_verbs[0]:
                    currentDict['pkg'] = ''
                    currentDict['ver'] = ''
                    currentDict['status'] = msgs[1]
                currentDict['msg'] = ''  # only good for warnings
                if not currentDict['msg']:
                    currentDict.pop('msg', None)
                if not currentDict['ver']:
                    currentDict.pop('ver', None)
                if not currentDict['pkg']:
                    currentDict.pop('pkg', None)
                if warm and currentDict['pkg']:
                    warm['pkg'] = currentDict['pkg']
                    warm = None
                yield currentDict

    def load_file(self):
        """load pacman log"""
        with open(self.logfile) as fin:
            return list(self.generate_dicts(fin))

    def save_file(self, items, jsonfile: str):
        """save logs in json file"""
        with open(jsonfile, 'w') as fout:
            json.dump(items, fout)

    def convert(self, jsonfile: str):
        self.save_file(self.load_file(), jsonfile)

    def load_json(self, jsonfile: str):
        with open(jsonfile) as fin:
            items = json.load(fin)
        for item in items:
            item['date'] = datetime.datetime.strptime(
                item['date'], '%Y-%m-%d %H:%M')
        return items
