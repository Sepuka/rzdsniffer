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
import rzd
from functools import partial

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
        self.info('<- Запрошен ресурс %s с IP %s', self.__class__.__name__, request.getClientIP())
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

resource = Resource()
try:
    # Любой ресурс может не завестись
    resource.putChild('station', StationSelector())
except Exception, ex:
    print ex
else:
    reactor.listenTCP(config.getint('webserver', 'port'), server.Site(resource))
    reactor.run()
