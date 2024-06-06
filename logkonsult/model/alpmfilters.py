"""
    filter json logs
"""

import datetime


class AlpmFilters():

    def filters(self, logs, verb: str = '', adate: str = '', package: str = ''):
        try:
            adate = datetime.datetime.strptime(adate, '%Y-%m-%d').date()
        except ValueError:
            adate = None
        for item in logs:
            try:
                if package:
                    if item['pkg'] != package:
                        continue
                if verb:
                    if item['verb'] != verb:
                        continue
                if adate:
                    diffdate = adate - item['date'].date()
                    if diffdate.days != 0:
                        continue
                yield item
            except KeyError:
                pass

    def updates(self, logs):
        for item in logs:
            try:
                if item['verb'] == 'upgraded':
                    yield item
            except KeyError:
                pass

    def package(self, logs, package: str):
        for item in logs:
            try:
                if item['pkg'] == package:
                    yield item
            except KeyError:
                pass

    def date(self, logs, adate: str):
        adate = datetime.datetime.strptime(adate, '%Y-%m-%d').date()
        for item in logs:
            try:
                diffdate = adate - item['date'].date()
                if diffdate.days == 0:
                    # print(diffdate)
                    yield item
            except KeyError:
                pass

    def package_names(self, logs):
        for item in logs:
            try:
                if item['verb'] == 'upgraded' or item['verb'] == 'installed':
                    yield item['pkg']
            except (TypeError, KeyError):
                pass

    def actions(self, logs):
        for item in logs:
            try:
                if item['verb'] == 'transaction' and item['status'] == 'started':
                    yield item
            except KeyError:
                pass
