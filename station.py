#! /usr/bin/python
# -*- coding: utf8 -*-
# Web-сервер принимающий запрос содержащий в себе имя станции (часть имени) и
# определяющей её код

__author__="shlomin"
__date__ ="$12.07.2013 12:04:30$"

from twisted.web import server
from twisted.web.resource import Resource
from twisted.internet import reactor
from ConfigParser import ConfigParser
from logger import Logger

config = ConfigParser()
config.read('./config.ini')

class StationSelector(object, Resource):

    _log    = None

    def render_POST(self, request):
        u"""Обработка запроса на поиск кода станции
        @param request: Запрос клиента
        @type request: twisted.http.request
        """
        self._log = Logger()
        self._log.info(u'Запрошен ресурс %s с IP %s', self.__class__.__name__, request.getClientIP())
        return '%s : %s : %s' % (type(request), dir(request), request.args);

resource = Resource()
resource.putChild('station', StationSelector())
reactor.listenTCP(config.getint('webserver', 'port'), server.Site(resource))
reactor.run()
