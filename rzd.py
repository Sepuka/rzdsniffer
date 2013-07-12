#! /usr/bin/python
# -*- coding: utf-8 -*-

# Модуль взаимодействующий с РЖД сайтом

__author__="shlomin"
__date__ ="$12.07.2013 13:41:37$"

from logger import Logger

class RZD(object):

    _log    = None

    def __init__(self):
        self._log = Logger()

    def getStations(self, stationName):
        self._log.debug('Поиск станции "%s"', stationName)