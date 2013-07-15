#! /usr/bin/python
# -*- coding: utf-8 -*-

# Модуль взаимодействующий с РЖД сайтом

__author__="shlomin"
__date__ ="$12.07.2013 13:41:37$"

import sys
import httplib
import json
from logger import Logger
import useragent
from twisted.web import client as twc

class RZD(object):

    _log            = None

    addr            = 'http://rzd.ru'
    # Количество станций выдаваемых клиенту
    stationsPacket  = 10

    def __init__(self):
        self._log = Logger()

    def httpConnection(scheme, host, port=None, key=None, cert=None):
        u"""
        Создание HTTP-соединения
        """
        if scheme == 'https':
            if port is None:
                port  = httplib.HTTPS_PORT
            conn = httplib.HTTPSConnection(host, port, key, cert)
        elif scheme == 'http':
            if port is None:
                port  = httplib.HTTP_PORT
            conn = httplib.HTTPConnection(host, port)
        else:
            raise Exception('unknow scheme %', scheme)
        return conn

    def getStations(self, stationName):
        u"""Получение списка станций соответствующих имени
        Возвращает список из self.stationsPacket станций
        """
        self._log.debug('Поиск станции "%s"', stationName)
        scheme, host, port, path = twc._parse(self.addr)
        req = '/suggester?stationNamePart=%s&lang=ru&lat=0&compactMode=y' % stationName
        result = None
        try:
            conn = httplib.HTTPConnection(host)
            headers = {'User-Agent': useragent.getRandomUserAgent(),
                'Accept': '*/*', 'X-Requested-With': 'XMLHttpRequest'}
            self._log.debug('Отправка запроса на %s', req)
            conn.request('GET', req, None, headers)
        except Exception, ex:
            from traceback import extract_tb, format_list
            error = '%s:\ntrace:\n%s' % (ex, '\n'.join(format_list(extract_tb(sys.exc_info()[2]))))
            self._log.critical('Failed station retrieve: %s',
                error)
        else:
            response = conn.getresponse()
            if (response.status != httplib.CREATED):
                self._log.error('Failed station retrieve "%s": answer code %s',
                    stationName, response.status)
            else:
                answer = response.read()
                try:
                    stations = json.loads(answer, 'utf-8')
                except Exception, ex:
                    self._log.error('Failed to decode JSON answer: %s', ex)
                else:
                    # Сортируем словарь по полю L
                    result = sorted(stations, key=lambda k:k['L'], reverse=True)[:self.stationsPacket]
        finally:
            if (isinstance(conn, httplib.HTTPConnection)):
                conn.close()
            return result