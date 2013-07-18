#! /usr/bin/python
# -*- coding: utf-8 -*-

# Кеширующий модуль

__author__="shlomin"
__date__ ="$16.07.2013 16:17:17$"

from logger import Logger
from db import DB
from ConfigParser import ConfigParser

config = ConfigParser()
config.read('./config.ini')

class Cacher(object):
    u"""Система кеширования запросов"""

    # Соединение с БД
    __conn          =   {'connection':None, 'cursor':None}
    _log            = None
    _db             = None
    # Счетчик выполняющихся в данный момент запросов
    __query         = 0

    def __init__(self):
        self._log = Logger()
        self._db = DB()

    def getStations(self, stationName):
        u"""Возвращает станции начинающиеся со строки"""
        self._db.execute('''SELECT * FROM `Stations` WHERE `Name` LIKE %s ORDER BY `S` DESC LIMIT 100''',
            ("%" + stationName + "%"))
        return self._db.getFetchAll(True)

    def setStations(self, stations):
        u'''Сохранение станций в кеше'''
        data = []
        for station in stations:
            data.append('("%s","%s","%s","%s")' % (station['c'], station['n'], station['S'], station['L']))
        self._db.execute('''INSERT IGNORE INTO `Stations` (`Code`, `Name`, `S`, `L`) VALUES %s''' % ','.join(data))
        self._db.getConnDB().commit()