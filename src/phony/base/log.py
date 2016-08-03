import logging
import string

from functools import wraps

MAXIMUM_TRACE_WIDTH = 40

def send_to_stdout(level = logging.DEBUG):
  logging.basicConfig(
    level = level,
    format = '%(asctime)s.%(msecs)03d %(name)-60s %(levelname)-8s %(message)s',
    datefmt = '%Y-%m-%d %H:%M:%S'
  )

class TypeLabel:
  def source(self, instance):
    return instance.__module__ + '.' + type(instance).__name__

  def call(self, instance, method, args, limit):
    if args and len(args) > 0:
      args = pretty_args(args[1:], limit)
    else:
      args = ''

    return type(instance).__name__ + '.' + method.__name__ + '(' + args + ')'

class InstanceLabel:
  def source(self, instance):
    return instance.__module__ + '.' + type(instance).__name__ + '.' + str(id(instance))

  def call(self, instance, method, args, limit):
    if args and len(args) > 0:
      args = pretty_args(args[1:], limit)
    else:
      args = ''

    type_and_instance = type(instance).__name__ + '.' + str(id(instance))
    return type_and_instance + '.' + method.__name__ + '(' + args + ')'

class Levels:
  CRITICAL = logging.CRITICAL
  ERROR = logging.ERROR
  WARNING = logging.WARNING
  INFO = logging.INFO
  DEBUG = logging.DEBUG
  DEFAULT = logging.DEBUG

  @classmethod
  def parse(cls, str):
    level = str.upper()
    if level == 'CRITICAL':
      return cls.CRITICAL
    elif level == 'ERROR':
      return cls.ERROR
    elif level == 'WARNING':
      return cls.WARNING
    elif level == 'INFO':
      return cls.INFO
    elif level == 'DEBUG':
      return cls.DEBUG
    elif level == 'DEFAULT':
      return cls.DEFAULT
    else:
      raise Exception('Unrecognized logging level: "' + str + '"')

class ScopedLogger(object):
  _label = ""
  _level = None
  _instance = None

  def __init__(self, name_or_instance, scope_label, log_level = Levels.DEBUG):
    if isinstance(name_or_instance, basestring):
      self._instance = NamedLogger(name_or_instance)
    elif name_or_instance:
      self._instance = name_or_instance
    else:
      raise Exception('Must provide a name or logger class instance')

    self._label = scope_label
    self._level = log_level

  def __enter__(self):
    self._instance.log().log(self._level, "-> " + self._label)

  def __exit__(self, exc_type, exc_value, traceback):
    self._instance.log().log(self._level, "<- " + self._label)

class NamedLogger(object):
  _log_name = ""
  _log = None
  _level = Levels.DEFAULT

  class TraceAs:
    @staticmethod
    def call(with_arguments = True, width = MAXIMUM_TRACE_WIDTH, log_level = Levels.DEFAULT, label_maker = TypeLabel()):
      def decorator(method):
        def call_wrapper(*args, **kwargs):
          instance = args[0]

          if log_level == Levels.DEFAULT:
            level = instance.log_level()
          else:
            level = log_level

          label = label_maker.call(instance, method, args if with_arguments else None, width)

          with ScopedLogger(instance, label, log_level) as scope:
            method(*args, **kwargs)

        return call_wrapper
      return decorator

    @staticmethod
    def event(with_arguments = True, width = MAXIMUM_TRACE_WIDTH, log_level = Levels.DEFAULT, label_maker = TypeLabel()):
      def decorator(method):
        def call_wrapper(*args, **kwargs):
          instance = args[0]

          if log_level == Levels.DEFAULT:
            level = instance.log_level()
          else:
            level = log_level

          label = label_maker.call(instance, method, args if with_arguments else None, width)
          label = '** ' + label + ' **'

          instance.log().log(level, label)

          method(*args, **kwargs)

        return call_wrapper
      return decorator

  def __init__(self, name):
    self._log_name = str(name)
    self._log = logging.getLogger(self._log_name)

  def log(self):
    return self._log

  def log_level(self, log_level = None):
    if log_level != None:
      self._level = log_level

    return self._level

  def log_name(self):
    return self._log_name

class ClassLogger(NamedLogger):
  def __init__(self, label_maker = TypeLabel()):
    name = label_maker.source(self)
    NamedLogger.__init__(self, name)

class InstanceLogger(NamedLogger):
  def __init__(self, label_maker = InstanceLabel()):
    name = label_maker.source(self)
    NamedLogger.__init__(self, name)

def pretty_args(args, limit):
  def stringify(s):
    try:
      s = str(s)
    except:
      s = '???'

    if len(s) > 0 and not (s[0] in string.printable):
      # Display the numeric value of the first unprintable character
      return str(ord(s[0]))
    else:
      return s

  val = ', '.join(filter(None, map(stringify, args)))
  if len(val) > limit:
    return val[:limit] + '...'
  else:
    return val

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