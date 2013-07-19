#! /usr/bin/python
# -*- coding: utf-8 -*-
# Web-сервер принимающий запрос содержащий в себе имя станции (часть имени) и
# определяющей её код

__author__="shlomin"
__date__ ="$12.07.2013 12:04:30$"

from twisted.web import server
from twisted.web.resource import Resource
from twisted.internet import reactor
from ConfigParser import ConfigParser
from logger import Logger, asciify
from db import DB
import rzd
from functools import partial
from urllib import urlencode
from datetime import datetime

config = ConfigParser()
config.read('./config.ini')

class StationSelector(object, Resource):

    _log    = None
    _rzd    = None
    # Словарь имен вызванных логов для partial
    _logNamesPart   = {}

    def __init__(self):
        self._log = Logger()
        self._rzd = rzd.RZD()

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

    def _output(self, response, request):
        u"""
        Выдача контента клиенту
        @param response: Строка с ответом клиенту
        @type response: C{str}
        @param request: Запрос клиента
        @type request: twisted.http.request
        @return None
        """
        request.setHeader('Content-Type', 'text/plain;charset=utf-8')
        if not isinstance(response, basestring):
            response = str(response)
        self.debug('-> %s', response)
        request.write(asciify(response))
        request.finish()

    def render_POST(self, request):
        u"""Обработка запроса на поиск кода станции
        @param request: Запрос клиента
        @type request: twisted.http.request
        """
        self.info('<- Запрошен ресурс с IP %s', request.getClientIP())
        try:
            station = request.args['station'][0]
        except KeyError:
            request.setResponseCode(400)
            self._output('expected station parameter', request)
            return server.NOT_DONE_YET
        else:
            stations = self._rzd.getStations(station)
            if (stations == None):
                self._output('Ошибка получения данных', request)
            else:
                self._output(stations, request)
        return server.NOT_DONE_YET

class Searcher(StationSelector):

    _db     = None

    def __init__(self):
        self._db = DB()
        super(Searcher, self).__init__()

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

    def render_POST(self, request):
        u"""Обработка запроса на поиск билетов
        @param request: Запрос клиента
        @type request: twisted.http.request
        """
        self.info('<- Запрошен ресурс с IP %s', request.getClientIP())
        answer = ''
        try:
            src = request.args['src'][0]
            dst = request.args['dst'][0]
            date = request.args['date'][0]
        except KeyError, ex:
            request.setResponseCode(400)
            self._output('expected some parameter: %s' % ex, request)
            return server.NOT_DONE_YET
        else:
            req = self._buildRequest(src, dst, date)
            if req is None:
                answer = 'bad request'
            else:
                self.debug('Собран запрос "%s"', req)
            self._output(answer, request)
        return server.NOT_DONE_YET

resource = Resource()
try:
    # Любой ресурс может не завестись
    resource.putChild('station', StationSelector())
    resource.putChild('search', Searcher())
except Exception, ex:
    print ex
else:
    reactor.listenTCP(config.getint('webserver', 'port'), server.Site(resource))
    reactor.run()
