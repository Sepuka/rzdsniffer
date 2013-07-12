# -*- coding: utf-8 -*-
# Модуль логирования

# Логирование в файл и ротация по времени
import logging
# Константы уровня логирования
from logging import CRITICAL, ERROR, WARNING, INFO, DEBUG
from logging.handlers import TimedRotatingFileHandler
# Конфиг
from ConfigParser import ConfigParser
import os, sys
from twisted.internet import threads

def process_sequence(func):
    u"""
    Декоратор обеспечивающий обработку всех элементов последовательности
    """
    def sequence(arg):
        if isinstance(arg, tuple) or isinstance(arg, list):
            return type(arg)(map(func, arg))
        elif isinstance(arg, dict):
            for key, value in arg.iteritems():
                arg[key] = func(value)
            return arg
        else:
            return func(arg)
    return sequence

@process_sequence
def asciify(data):
    u"""
    Приведение данных к ascii кодеку
    """
    if isinstance(data, unicode):
        return data.encode('utf-8')
    return data

@process_sequence
def utf8fy(data):
    u"""
    Приведение данных в unicode
    """
    if not isinstance(data, unicode):
        try:
            return unicode(data, 'utf-8')
        except (TypeError):
            return unicode(data)
    return data

class Singltone(type):
    def __init__(cls, *args, **kw):
        cls.instance = None

    def __call__(cls, *args, **kw):
        if cls.instance is None:
            cls.instance = super(Singltone, cls).__call__(*args, **kw)
        return cls.instance

class Logger(object):
    __metaclass__   = Singltone
    __conf          = None
    __log           = None
    __handler       = None

    def __init__(self):
        self.__conf = config = ConfigParser()
        self.__conf.read('./config.ini')
        # Пути к файлам и время ротации
        LOG_FILE = self.__conf.get('log', 'path')
        LOG_WHEN = 'midnight'

        self.__handler = logging.handlers.TimedRotatingFileHandler(LOG_FILE, when=LOG_WHEN)
        self.__handler.setFormatter(logging.Formatter('%(asctime)-15s %(levelname)-8s %(message)s'))
        self.__handler.setLevel(logging.DEBUG)
        error_handler = logging.handlers.SMTPHandler(self.__conf.get('log', 'smtp'),
            'rzdparser@xn--h1afdfc2d.xn--p1ai', self.__conf.get('log', 'adminMail'),
            'RZDParser')
        error_handler.setFormatter(logging.Formatter('%(asctime)-15s %(levelname)-8s %(message)s'))
        error_handler.setLevel(self.__conf.getint('log', 'mailLevel'))

        self.__log = logging.getLogger('rzdparser')
        self.__log.setLevel(logging.DEBUG)
        self.__log.addHandler(self.__handler)
        self.__log.addHandler(error_handler)

    def __del__(self):
        self.__log.shutdown()

    def _log(self, msg, *args, **kw):
        """
        Запись в лог
        """
        try:
            kw['exc_info']
        except KeyError:
            exc_info = False
        else:
            exc_info = sys.exc_info()
        msg = msg % asciify(args)
        # SMTP лог может быть достаточно долгим
        threads.deferToThread(self.__log.log, kw['level'], asciify(msg), exc_info=exc_info)

    def flush(self):
        """
        Принудительный сброс логов
        """
        self.__handler.flush()

    def debug(self, msg, *args, **kwargs):
        """
        Запись в лог типа DEBUG
        """
        kwargs['level'] = DEBUG
        self._log(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        """
        Запись в лог типа INFO
        """
        kwargs['level'] = INFO
        self._log(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        """
        Запись в лог типа WARNING
        """
        kwargs['level'] = WARNING
        self._log(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        """
        Запись в лог типа ERROR
        """
        kwargs['level'] = ERROR
        self._log(msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        """
        Запись в лог типа CRITICAL
        """
        kwargs['level'] = CRITICAL
        self._log(msg, *args, **kwargs)
