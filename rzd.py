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
from datetime import datetime
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

    # Логи
    _log            = None
    _db             = None
    # Кеш
    _cache          = None
    # Словарь имен вызванных логов для partial
    _logNamesPart   = {}

    # Количество станций выдаваемых клиенту
    stationsPacket  = 10

    def __init__(self):
        self._log = Logger()
        self._cache = Cacher()
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
                    'Cookie': '''_POSTED_BALLOT_ID=981; LtpaToken2=/M7wkUeaHRHGGj0q9mq9ORUfGY7rvp+Izd31zhR1E0Xi216h42Jq/thD/H7/vCmOC3QTG3kdCfiwDS7vhVo9c/W6XKyPWvm+rU1r8uGe7Q9SbrzI44chAuWGuTbMuxEkQQk28MUNz7obBztyGrl5oacOkQR9nrW4SCp47duSyXN33BqwDAfGkw8qxFi2VSmU6fhrwfn/2EoEIiSQPtAFJ9WUfX1r+3Yz5evU9CzpV/uHFjplJfjPQeSbky/+sqh2JRvqRlqZ3+YeSHWQChvL73/RybpmvRwclvt9dk9tSMKOoJePE2O8b+1JibJZW8PCha5i4zV3FQ9E4CkShgsSKsd/9jMQS6BC21p2ANIE2N+T2ieIg0qEdt5eNnOHBHo9oLawp5JOYqV5Ekq6jOr1+r+u8Vd+uo+i53vE08rrxELLBB6SRGcR0MAmURU/4LXRFb7J7PxVRsvsh4O25Z9zelTDWNmtTAnaN2ZBnbhbpwqi9/xnP1licCBiKi+TT5AyCCzbULj6S7VyZ5mXoPbUGnUTLi9Bt6I+N4CpTNZekvFwlFEhulvaRGkkI11KL6XAUqcetQiWtLUyAZaOa4xEqht+GZSnNuvFXMhy3XyWQby/1q9RNOmMblzqN4DKI8KN; __utma=10532855.1297015581.1375874990.1375874990.1375878680.2; __utmc=10532855; __utmz=10532855.1375874990.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none); __utma=53259433.1315264599.1375875002.1375875002.1375878916.2; __utmc=53259433; __utmz=53259433.1375878916.2.2.utmcsr=rzd.ru|utmccn=(referral)|utmcmd=referral|utmcct=/; JSESSIONID=0000m0wmF2CAM2dsUb3ZzU1NYim:17obq94ai; lang=ru'''}
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