import logging
from functools import wraps

def send_to_stdout(level = logging.DEBUG):
  logging.basicConfig(
    level = level,
    format = '%(asctime)s.%(msecs)03d %(name)-60s %(levelname)-8s %(message)s',
    datefmt = '%Y-%m-%d %H:%M:%S'
  )

class Levels:
  CRITICAL = logging.CRITICAL
  ERROR = logging.ERROR
  WARNING = logging.WARNING
  INFO = logging.INFO
  DEBUG = logging.DEBUG
  DEFAULT = logging.DEBUG

class ScopedLogger(object):
  __scope = ""
  __level = None
  __instance = None

  def __init__(self, logger_instance, scope_name, log_level = Levels.DEBUG):
    self.__instance = logger_instance
    self.__scope = scope_name
    self.__level = log_level

  def __enter__(self):
    self.__instance.log().log(self.__level, "-> " + self.__scope)

  def __exit__(self, exc_type, exc_value, traceback):
    self.__instance.log().log(self.__level, "<- " + self.__scope)

class NamedLogger(object):
  __log_name = ""
  __log = None
  __level = Levels.DEFAULT

  class TraceAs:
    @staticmethod
    def call(method):
      def inner(*args, **kwargs):
        instance = args[0]
        with ScopedLogger(instance, method.__name__ + "()") as scope:
          method(*args, **kwargs)
      return inner

    @staticmethod
    def event(method):
      def inner(*args, **kwargs):
        instance = args[0]
        instance.log().log(instance.log_level(), "** " + method.__name__ + " **")
        method(*args, **kwargs)
      return inner

  def __init__(self, name):
    self.__log_name = name
    self.__log = logging.getLogger(name)

  def log(self):
    return self.__log

  def log_level(self, log_level = None):
    if log_level != None:
      self.__level = log_level

    return self.__level

  def log_name(self):
    return self.__log_name

class ClassLogger(NamedLogger):
  def __init__(self):
    name = self.__module__ + "." + type(self).__name__
    NamedLogger.__init__(self, name)

class InstanceLogger(NamedLogger):
  def __init__(self):
    name = "%s.%s(%s)" % (
      self.__module__,
      type(self).__name__,
      id(self)
    )
    NamedLogger.__init__(self, name)

# def _log_public_method(method):
#     @wraps(method)
#     def wrapper(*a, **ka):
#         self = a[0]

#         log_it = False
#         if not method.__name__.startswith("__"):
#           log_it = True
#           self.log().log(self.log_level(), "--> " + method.__name__)

#         val = method(*a, **ka)

#         if log_it:
#           self.log().log(self.log_level(), "<-- " + method.__name__)

#         return val

#     return wrapper

# class MethodLogger(type):
#   def __new__(cls, cls_name, bases, attrs):
#     for name, method in attrs.items():
#       if callable(method):
#         attrs[name] = _log_public_method(method)
#       elif isinstance(method, (classmethod, staticmethod)):
#         attrs[name] = type(method)(_log_public_method(method.__func__))
#     return type.__new__(cls, cls_name, bases, attrs)

# class ClassMethodLogger(ClassLogger):
#   __metaclass__ = MethodLogger

#   def __init__(self, log_level = Levels.DEBUG):
#     ClassLogger.__init__(self)
#     self.log_level(log_level)