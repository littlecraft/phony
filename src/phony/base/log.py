import string
import logging
import inspect

from functools import wraps

MAXIMUM_TRACE_WIDTH = 40

def send_to_stdout(level = logging.DEBUG):
  logging.basicConfig(
    level = level,
    format = '%(asctime)s.%(msecs)03d %(name)-60s %(levelname)-8s %(message)s',
    datefmt = '%Y-%m-%d %H:%M:%S'
  )

def static(name):
  return logging.getLogger(name)

class TypeLabel:
  def source(self, instance):
    return instance.__module__ + '.' + type(instance).__name__

  def call(self, instance, method, args, limit):
    if args and len(args) > 0:
      args = pretty_args(args[1:], limit)
    else:
      args = ''

    if not isinstance(method, basestring):
      method = method.__name__

    return type(instance).__name__ + '.' + method + '(' + args + ')'

class InstanceLabel:
  def source(self, instance):
    return instance.__module__ + '.' + type(instance).__name__ + '.' + str(id(instance))

  def call(self, instance, method, args, limit):
    if args and len(args) > 0:
      args = pretty_args(args[1:], limit)
    else:
      args = ''

    if not isinstance(method, basestring):
      method = method.__name__

    type_and_instance = type(instance).__name__ + '.' + str(id(instance))
    return type_and_instance + '.' + method + '(' + args + ')'

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
  _label_maker = None
  _level = Levels.DEFAULT

  class TraceAs:
    @staticmethod
    def call(with_arguments = True, width = MAXIMUM_TRACE_WIDTH, log_level = Levels.DEFAULT):
      def decorator(method):
        def call_wrapper(*args, **kwargs):
          instance = args[0]

          with instance.log().call(method, args if with_arguments else None, width, log_level):
           return method(*args, **kwargs)

        return call_wrapper
      return decorator

    @staticmethod
    def event(with_arguments = True, width = MAXIMUM_TRACE_WIDTH, log_level = Levels.DEFAULT):
      def decorator(method):
        def call_wrapper(*args, **kwargs):
          instance = args[0]

          instance.log().event(method, args if with_arguments else None, width, log_level)

          return method(*args, **kwargs)

        return call_wrapper
      return decorator

  def __init__(self, name_or_label_maker):
    if isinstance(name_or_label_maker, basestring):
      self._log_name = str(name_or_label_maker)
      self._label_maker = TypeLabel()
    else:
      self._log_name = name_or_label_maker.source(self)
      self._label_maker = name_or_label_maker

    self._log = logging.getLogger(self._log_name)

    # Add mixin methods to logger instance:
    self._log.variable = self._variable
    self._log.event = self._log_event_with_method_label
    self._log.call = self._log_method_call

  def log(self):
    return self._log

  def log_level(self, log_level = None):
    if log_level != None:
      self._level = log_level

    return self._level

  def log_name(self):
    return self._log_name

  def _variable(self, variable, value, label = '', with_arguments = True, width = MAXIMUM_TRACE_WIDTH, level = Levels.DEFAULT):
    if level == Levels.DEFAULT:
      level = self.log_level()

    if label == '':
      (instance, method_name, args) = NamedLogger._calling_instance_method_name_and_args(1)
      label = self._label_maker.call(instance, method_name, args if with_arguments else None, width)

    if label:
      self._log.log(level, '%s => %s = %s' % (label, variable, value))
    else:
      self._log.log(level, '%s = %s' % (variable, value))

  def _log_event_with_method_label(self, method = None, args = None, width = MAXIMUM_TRACE_WIDTH, level = Levels.DEFAULT):
    if level == Levels.DEFAULT:
      level = self.log_level()

    if not method:
      (instance, method_name, args) = NamedLogger._calling_instance_method_name_and_args(1)
      label = self._label_maker.call(instance, method_name, args if with_arguments else None, width)
    else:
      label = self._label_maker.call(self, method, args, width)

    self._log.log(level, '** %s' % label)

  def _log_method_call(self, method = None, args = None, width = MAXIMUM_TRACE_WIDTH, level = Levels.DEFAULT):
    if level == Levels.DEFAULT:
      level = self.log_level()

    if not method:
      (instance, method_name, args) = NamedLogger._calling_instance_method_name_and_args(1)
      label = self._label_maker.call(instance, method_name, args if with_arguments else None, width)
    else:
      label = self._label_maker.call(self, method, args, width)

    return ScopedLogger(self, label, level)

  @staticmethod
  def _calling_instance_method_name_and_args(frame_level = 0):
    clazz = ''
    caller_args = []
    method_name = ''

    frame = NamedLogger._calling_frame(frame_level + 1)
    frame_info = inspect.getframeinfo(frame)
    method_name = frame_info[2]

    args, _, _, values = inspect.getargvalues(frame)
    if len(args) and args[0] == 'self':
      instance = values.get('self', None)

    caller_args = map(lambda arg: values[arg], args)

    return (instance, method_name, caller_args)

  @staticmethod
  def _calling_frame(frame_level = 0):
    cur_frame = inspect.currentframe()
    calling_frame = inspect.getouterframes(cur_frame, frame_level + 2)

    return calling_frame[1 + frame_level][0]

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