#! /usr/bin/python
# -*- coding: utf-8 -*-

# Модуль взаимодействующий с РЖД сайтом

__author__="shlomin"
__date__ ="$12.07.2013 13:41:37$"

from logger import Logger, asciify
import useragent
from cacher import Cacher
from db import DB

import sys
import httplib
import json
from twisted.web import client as twc
from functools import partial
from datetime import datetime, timedelta
from urllib import urlencode

# Плацкарт
RESERVED_SEAT   = 1
# Общий
COMMON_CAR      = 2
# Сидячий
SEDENTARY_CAR   = 3
# Купе
STATEROOM       = 4
# Мягкий
SOFT_CAR        = 5
# Люкс
LUXURY_CAE      = 6

class RZD(object):

    _instance       = None
    # Логи
    _log            = None
    _db             = None
    # Кеш
    _cache          = None
    # Словарь имен вызванных логов для partial
    _logNamesPart   = {}
    # Куки для сайта
    _cookie         = None

    # Количество станций выдаваемых клиенту
    stationsPacket  = 10

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(RZD, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        if not self._log:
            self._log = Logger()
        if not self._cache:
            self._cache = Cacher()
        if not self._db:
            self._db = DB()
        if not self._cookie:
            self._setCookie()

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
        u'''Строит запрос для РЖД'''
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
            date0 = datetime.strptime(date, '%Y-%m-%d').strftime('%d.%m.%Y')
            nextDay = datetime.strptime(date, '%Y-%m-%d') + timedelta(days=1)
            date1 = nextDay.strftime('%d.%m.%Y')
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
            'dt0': date0,
            'st1': dstName,
            'code1': dst,
            'dt1': date1,
            'SESSION_ID': 1
        }
        return urlencode(params)

    def getStations(self, stationName):
        u"""Получение списка станций соответствующих имени
        Возвращает список из self.stationsPacket станций
        """
        self.debug('Поиск станции "%s"', stationName)
        addr = 'http://rzd.ru'
        stations = self._cache.getStations(stationName)
        # Если в кеше пусто или мало данных, отправляемся в интернет
        if (stations == None or len(stations) < self.stationsPacket):
            scheme, host, port, path = twc._parse(addr)
            req = '/suggester?stationNamePart=%s&lang=ru&lat=0&compactMode=y' % stationName
            result = None
            try:
                conn = httplib.HTTPConnection(host)
                headers = {'User-Agent': useragent.getRandomUserAgent(),
                    'Accept': '*/*', 'X-Requested-With': 'XMLHttpRequest'}
                self.debug('Отправка запроса на %s', req)
                conn.request('GET', req, None, headers)
            except Exception, ex:
                from traceback import extract_tb, format_list
                error = '%s:\ntrace:\n%s' % (ex, '\n'.join(format_list(extract_tb(sys.exc_info()[2]))))
                self.critical('Failed station retrieve: %s',
                    error)
            else:
                response = conn.getresponse()
                if (response.status != httplib.CREATED):
                    self.error('Failed station retrieve "%s": answer code %s',
                        stationName, response.status)
                else:
                    answer = response.read()
                    try:
                        stations = json.loads(answer, 'utf-8')
                    except Exception, ex:
                        self.error('Failed to decode JSON answer: %s', ex)
                    else:
                        #TODO: можно распараллелить запись в кеш
                        self._cache.setStations(stations)
            finally:
                if (isinstance(conn, httplib.HTTPConnection)):
                    conn.close()
        else:
            self.debug('Ответ взят из кеша')

        # Сортируем словарь по полю L
        result = sorted(stations, key=lambda k:k['L'], reverse=True)[:self.stationsPacket]
        return json.dumps(result, ensure_ascii=False)

    def _setCookie(self):
        u'''
        Сохранение куков
        Задача метода состоит в получении сессии, а конкретно параметра JSESSIONID
        '''
        self._cookie = ''
        addr = 'http://pass.rzd.ru/timetable/public/ru?STRUCTURE_ID=735&layer_id=5354&refererVpId=1&refererPageId=704&refererLayerId=4065#dir=0|tfl=3|checkSeats=1|st0=%D0%A1%D0%90%D0%9D%D0%9A%D0%A2-%D0%9F%D0%95%D0%A2%D0%95%D0%A0%D0%91%D0%A3%D0%A0%D0%93|code0=2004000|dt0=20.08.2013|st1=%D0%9A%D0%A3%D0%A0%D0%A1%D0%9A|code1=2000150|dt1=20.08.2013'
        scheme, host, port, path = twc._parse(addr)
        try:
            conn = httplib.HTTPConnection(host)
            headers = {'User-Agent': useragent.getRandomUserAgent()}
            self.debug('Получение cookies')
            conn.request('GET', path, None, headers)
        except Exception, ex:
            from traceback import extract_tb, format_list
            error = '%s:\ntrace:\n%s' % (ex, '\n'.join(format_list(extract_tb(sys.exc_info()[2]))))
            self.critical('Failed trains retrieve: %s',
                error)
            raise ex
        else:
            response = conn.getresponse()
            cookie = [i[1] for i in response.getheaders() if i[0] == "set-cookie"][0]
            for i in cookie.split(';'):
                posSession = i.find('JSESSIONID')
                if posSession != -1:
                    self._cookie = self._cookie + i[posSession:]
            self.debug('Cookie: %s', self._cookie)

    def _getTrainsRequest(self, req):
        u'''
        Отправка запроса в РЖД
        Возвращает строковый ответ сервера
        '''
        addr = 'http://pass.rzd.ru'
        scheme, host, port, path = twc._parse(addr)
        try:
            conn = httplib.HTTPConnection(host)
            headers = {'User-Agent': useragent.getRandomUserAgent(),
                    'Accept': '*/*', 'X-Requested-With': 'XMLHttpRequest',
                    'Cookie': self._cookie}
            self.debug('Отправка запроса на %s', req)
            conn.request('GET', req, None, headers)
        except Exception, ex:
            from traceback import extract_tb, format_list
            error = '%s:\ntrace:\n%s' % (ex, '\n'.join(format_list(extract_tb(sys.exc_info()[2]))))
            self.critical('Failed trains retrieve: %s',
                error)
            raise ex
        else:
            response = conn.getresponse()
            if response.status != httplib.OK:
                self.error('Failed trains retrive: answer code %s', response.status)
                if (isinstance(conn, httplib.HTTPConnection)):
                    conn.close()
                raise Exception('bad response status when trains retrieve')
            else:
                answer = response.read()
                if (isinstance(conn, httplib.HTTPConnection)):
                    conn.close()
                return answer

    def getTrains(self, src, dst, date):
        u'''Получение списка поездов'''
        self.debug('Получение списка поездов по маршруту %s-%s на %s', src, dst, date)
        # Строим запрос для РЖД
        req = self._buildRequest(src, dst, date)
        # Запрос может не получится, например, из-за несуществующей переденной станции
        if req is None:
            raise Exception('Failed build request')
        req = '/timetable/public/ru?%s' % req
        answer = self._getTrainsRequest(req)
        try:
            trains = json.loads(answer, 'utf-8')
            self.debug(str(trains))
            if trains.has_key('result') and trains['result'] == 'Error':
                self.warning('Запрос не удался: %s', trains['message'])
                if trains.has_key('sessExpired') and trains['sessExpired'] == 1:
                    self.debug('Получен признак истекшей сессии')
            # Первый запрос даст нам параметр rid
            try:
                req += '&rid=%s' % trains['rid']
            except KeyError:
                raise Exception(asciify(trains['tp'][0]['msgList'][0]['message']))
            answer = self._getTrainsRequest(req)
            try:
                trains = json.loads(answer, 'utf-8')
                self.debug(str(trains))
            except Exception, ex:
                self.error('Failed to decode JSON answer. Error: %s,  Text: %s', ex, answer)
                raise Exception('bad JSON when trains retrieve')
            #print trains['tp'][0]['msgList'][0]['message']
        except ValueError, ex:
            self.error('Failed to decode JSON answer. Error: %s,  Text: %s', ex, answer)
            raise Exception('bad JSON when trains retrieve')