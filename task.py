#! /usr/bin/python
# -*- coding: utf-8 -*-

__author__="shlomin"
__date__ ="$19.07.2013 12:40:35$"

from logger import Logger
from db import DB
from ConfigParser import ConfigParser
from urllib import urlencode
from datetime import datetime
from functools import partial

IN_PROGRESS = 0
COMPLERE = 1

config = ConfigParser()
config.read('./config.ini')

class Task(object):
    u"""
    Класс управления заданиями
    Позволяет добавлять и удалять задания из очереди
    """
    _db             = None
    # Логи
    _log            = None
    # Словарь имен вызванных логов для partial
    _logNamesPart   = {}

    def __init__(self):
        self._log = Logger()
        self._db = DB()

    def __getattr__(self, name):
        try:
            return self._logNamesPart[name]
        except KeyError:
            obj = getattr(self._log, name)
            if obj is not None:
                part = partial(obj, moduleName=self.__class__.__name__)
                self._logNamesPart[name] = part
                return part
            else:
                self._log.error('Попытка вызова несуществующего типа лога "%s"',
                    name, moduleName=self.__class__.__name__)

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

    def cnt(self):
        u'''
        Получение количества активных заданий в системе
        @return int
        '''
        self._db.execute('''SELECT COUNT(*) FROM `Tasks` WHERE `Complete`=%s''',
            IN_PROGRESS)
        return int(self._db.getFetchOne()[0])

    def add(self, src, dst, date, phone, type):
        u'''Добавление нового задания в очередь'''
        limit = config.getint('system', 'taskLimit')
        if limit > self.cnt():
            self._db.execute('''INSERT INTO `Tasks` SET `Phone`=%s, `Src`=%s,
                `Dst`=%s, `Date`=%s, `Type`=%s, `DateTimeCreate`=NOW(), `DateTimeCheck`=null, `Complete`=0''',
                phone, int(src), int(dst), date, type)
            self._db.getConnDB().commit()
            self.debug('Клиент %s добавил новую заявку', phone)
        else:
            self.error('Система не может принять %d-ю заявку', self.cnt())
            raise Exception('Достигнут лимит количества активных заданий в системе')