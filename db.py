#! /usr/bin/python
# -*- coding: utf-8 -*-

__author__="shlomin"
__date__ ="$18.07.2013 12:25:14$"

import MySQLdb
# Поддержание соединения с СУБД
from twisted.internet import reactor
from ConfigParser import ConfigParser

config = ConfigParser()
config.read('./config.ini')

#! /usr/bin/python
# -*- coding: utf-8 -*-

# Кеширующий модуль

__author__="shlomin"
__date__ ="$16.07.2013 16:17:17$"

import MySQLdb
# Поддержание соединения с СУБД
from twisted.internet import reactor
from logger import Logger
from ConfigParser import ConfigParser

config = ConfigParser()
config.read('./config.ini')

class DBException(Exception):
    u"""Класс исключений"""
    def __init__(self, msg, code = 'Error'):
        self.msg    = msg
        self.code   = code

    def __str__(self):
        return self.msg

    def getErrorMessage(self):
        return self.msg

    def getTraceback(self):
        return ''

    def raiseException(self):
        raise self

class DB(object):
    u"""БД"""

    # Соединение с БД
    __conn          =   {'connection':None, 'cursor':None}
    _log            = None
    # Счетчик выполняющихся в данный момент запросов
    __query         =   0

    def __init__(self):
        self._log = Logger()
        self.__connect()
        self.__connection_checker()

    def __del__(self):
        """Деструктор объекта"""
        self.__conn['connection'].commit()
        self.__conn['cursor'].close()
        self.__conn['connection'].close()

    @property
    def cursor(self):
        return self.__conn['cursor']

    def __connect(self):
        """Соединение с БД"""
        dbSettings = {
            'host': config.get('db', 'host'),
            'port': config.getint('db', 'port'),
            'user': config.get('db', 'user'),
            'passwd': config.get('db', 'pass'),
            'db': config.get('db', 'name')}
        if self.__conn['connection'] is None:
            try:
                self.__conn['connection'] = MySQLdb.connect(charset='utf8', **dbSettings)
                self.__conn['cursor'] = self.__conn['connection'].cursor()
            except Exception, ex:
                raise Exception('Failed MySQL connect: %s' % ex)

    def __connection_checker(self):
        """Проверка установленного соединения с БД"""
        try:
            self.execute('SELECT 1')
        except (DBException,), e:
            self._log.warning('connection is gone away. try reconnect')
            self.__conn['connection'] = None
            self.__connect()
        reactor.callLater(config.getint('db', 'wait_timeout'), self.__connection_checker)

    def execute(self, query, *params, **kw):
        u"""
            Выполнение SQL-запроса с параметрами
            ************************************
            Получает шаблон запроса и параметры, а также идентификатор соединения
            Пытается выполнить запрос в свободное время рекурсивно вызывая себя
            Возвращает идентификатор последней вставленной строки
        """
        try:
            if kw['cursor'] is not None:
                cursor = kw['cursor']
            else:
                cursor = self.__conn['cursor']
        except (KeyError):
            cursor = self.__conn['cursor']
        if self.__query > 0:
            t = float('0.%d' % randint(1,9))
            self._log.warning('db busy, sleep %s sec. cursor %s\nquery %s\nparams %s', t, cursor, query, params)
            sleep(t)
            return self.execute(query, *params, **kw)
        self.__query += 1
        try:
            cursor.execute(query, params)
            if cursor._warnings:
                raise DBException('Warning detected!', 'warning')
        except (MySQLdb.Error, MySQLdb.IntegrityError), e:
            self._log.error('Mysql runtime error %d: %s', e.args[0], e.args[1])
            raise DBException(e.args[1], e.args[0])
        else:
            lastID = cursor.lastrowid
        finally:
            self.__query -= 1
        return lastID

    def getConnDB(self):
        u"""Получение ресурса БД"""
        return self.__conn['connection']

    def getFetchOne(self):
        """Получение одиночного результата выборки"""
        return self.cursor.fetchone()

    def getFetchAll(self, withFieldsName=False):
        u"""Извлечение всех строк данных
        Возвращает кортеж, а если передать withFieldsName=True, то список словарей
        """
        if withFieldsName == True:
            answer = []
            fields = [i[0] for i in self.cursor.description]
            for station in self.cursor.fetchall():
                dict = {}
                for (cnt, el) in enumerate(station):
                    dict[fields[cnt]] = el
                answer.append(dict)
            return answer
        else:
            return self.cursor.fetchall()

    def getRowCount(self):
        u"""Получение количества строк в кортеже"""
        return self.cursor.rowcount