import logging

def send_to_stdout(level = logging.DEBUG):
  logging.basicConfig(
    level = level,
    format = '%(asctime)s.%(msecs)03d %(name)-30s %(levelname)-8s %(message)s',
    datefmt = '%Y-%m-%d %H:%M:%S'
  )

class Levels:
  CRITICAL = logging.CRITICAL
  ERROR = logging.ERROR
  WARNING = logging.WARNING
  INFO = logging.INFO
  DEBUG = logging.DEBUG
  DEFAULT = logging.DEBUG

class NamedLogger(object):
  __log = None

  def __init__(self, name):
    self.__log = logging.getLogger(name)

  def log(self):
    return self.__log

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

class ScopedLogger(ClassLogger):
  __scope = ""
  __level = None
  def __init__(self, scope_name, level = Levels.DEBUG):
    self.__scope = scope_name
    self.__level = level
    ClassLogger.__init__(self)

  def __enter__(self):
    self.log().log(self.__level, "--> " + self.__scope)

  def __exit__(self, exc_type, exc_value, traceback):
    self.log().log(self.__level, "<-- " + self.__scope)