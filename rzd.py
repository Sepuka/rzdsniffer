#! /usr/bin/python
# -*- coding: utf-8 -*-

# Модуль взаимодействующий с РЖД сайтом

__author__="shlomin"
__date__ ="$12.07.2013 13:41:37$"

import sys
import httplib
from logger import Logger
from twisted.web import client as twc

class RZD(object):

    _log    = None

    addr = 'http://rzd.ru'

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
        """
        self._log.debug('Поиск станции "%s"', stationName)
        scheme, host, port, path = twc._parse(self.addr)
        req = '/suggester?stationNamePart=%s&lang=ru&lat=0&compactMode=y' % stationName
        try:
            conn = httplib.HTTPConnection(host)
            headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/28.0.1500.71 Safari/537.36',
                'Accept': '*/*', 'X-Requested-With': 'XMLHttpRequest'}
            self._log.debug('Отправка запроса на %s', req)
            conn.request('GET', req, None, headers)
        except Exception, ex:
            from traceback import extract_tb, format_list
            error = '%s:\ntrace:\n%s' % (ex, '\n'.join(format_list(extract_tb(sys.exc_info()[2]))))
            self._log.critical('Failed station retrieve: %s',
                error)
            return None
        else:
            response = conn.getresponse()
            if (response.status != httplib.CREATED):
                self._log.error('Failed station retrieve "%s": answer code %s',
                    stationName, response.status)
                return None
            return response.read()
        finally:
            if (isinstance(conn, httplib.HTTPConnection)):
                conn.close()