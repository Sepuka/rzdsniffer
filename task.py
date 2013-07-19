#! /usr/bin/python
# -*- coding: utf-8 -*-

__author__="shlomin"
__date__ ="$19.07.2013 12:40:35$"

from logger import Logger
from db import DB
from urllib import urlencode
from datetime import datetime

class Task(object):
    _db     = None

    def __init__(self):
        self._db = DB()

    def _buildRequest(self, src, dst, date):
        self._db.execute('''SELECT `Name` FROM `Stations` WHERE `Code`=%s''', int(src))
        if self._db.getRowCount():
            srcName = self._db.getFetchOne()
        else:
            self.error('Source station not found "%s"', src)
            return None
        self._db.execute('''SELECT `Name` FROM `Stations` WHERE `Code`=%s''', int(dst))
        if self._db.getRowCount():
            dstName = self._db.getFetchOne()
        else:
            self.error('Destionation station not found "%s"', dst)
            return None
        try:
            date = datetime.strptime(date, '%Y-%m-%d').strftime('%d.%m.%Y')
        except ValueError:
            self.error('Wrong format date "%s"', date)
            return None
        params = {
            'STRUCTURE_ID': 735,
            'layer_id': 5371,
            'dir': 0,
            'tfl': 3,
            'checkSeats': 1,
            'st0': srcName,
            'code0': src,
            'dt0': date,
            'st1': dstName,
            'code1': dst,
            'dt1': date,
            'SESSION_ID': 1
        }
        return urlencode(params)

    def add(self, src, dst, date, phone, type):
        u'''Добавление нового задания в очередь'''
        self._db.execute('''INSERT INTO `Tasks` SET `Phone`=%s, `Src`=%s,
            `Dst`=%s, `Date`=%s, `Type`=%s, `DateTimeCreate`=NOW(), `DateTimeCheck`=null, `Complete`=0''',
            phone, src, dst, date, type)
        self._db.getConnDB().commit()