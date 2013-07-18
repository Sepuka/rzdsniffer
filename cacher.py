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
        return

    def setStations(self, stations):
        pass