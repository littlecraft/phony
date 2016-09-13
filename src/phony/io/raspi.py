import time
import copy
import gobject

from phony.base.log import ClassLogger
from RPi import GPIO
from types import MethodType

class Inputs(ClassLogger):
  _layout = {}
  _inputs_by_channel = {}

  _rising_callback_by_channel_name = {}
  _falling_callback_by_channel_name = {}
  _pulse_callback_by_channel_name = {}

  def __init__(self, layout):
    ClassLogger.__init__(self)

    # IO event callbacks occur in another thread, dbus/gdk need
    # to be made aware of this.
    gobject.threads_init()

    GPIO.setmode(GPIO.BCM)

    self._layout = layout
    for name, config in layout.iteritems():
      for point in ['pin', 'pull_up_down']:
        Inputs._raise_if_not_in(point, config)

      config = copy.deepcopy(config)
      config['name'] = name

      self._inputs_by_channel[config['pin']] = config
      self._configure_input(name, config)

  def on_rising_edge(self, channel_name, callback):
    self._rising_callback_by_channel_name[channel_name] = callback

  def on_falling_edge(self, channel_name, callback):
    self._falling_callback_by_channel_name[channel_name] = callback

  def on_pulse(self, channel_name, callback):
    self._pulse_callback_by_channel_name[channel_name] = callback

  #@ClassLogger.TraceAs.call()
  def _channel_changed(self, channel):
    name = self._inputs_by_channel[channel]['name']

    do_rise = name in self._rising_callback_by_channel_name
    do_fall = name in self._falling_callback_by_channel_name

    if do_rise or do_fall:
      time.sleep(0.01)

      if GPIO.input(channel):
        high = 1
      else:
        high = 0

      if high and do_rise:
        self._rising_callback_by_channel_name[name]()

      if not high and do_fall:
        self._falling_callback_by_channel_name[name]()

    if name in self._pulse_callback_by_channel_name:
      self._pulse_callback_by_channel_name[name]()

  def _configure_input(self, name, configuration):
    pin = configuration['pin']

    self.log().debug('Pin %d -> %s' % (pin, name))

    if configuration['pull_up_down'] == 'up':
      pull_up_or_down = GPIO.PUD_UP
    else:
      pull_up_or_down = GPIO.PUD_DOWN

    if 'debounce' in configuration:
      debounce = configuration['debounce']
    else:
      debounce = 0

    GPIO.setup(pin, GPIO.IN, pull_up_down = pull_up_or_down)
    GPIO.add_event_detect(pin, GPIO.BOTH, callback = self._channel_changed, bouncetime = debounce)

  @staticmethod
  def _raise_if_not_in(point, config):
    if point not in config:
      raise Exception('Missing required configuration point %s' % point)

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    for channel in self._inputs_by_channel:
      GPIO.remove_event_detect(channel)

class Outputs(ClassLogger):
  _layout = None

  def __init__(self, layout):
    ClassLogger.__init__(self)

    # IO event callbacks occur in another thread, dbus/gdk need
    # to be made aware of this.
    gobject.threads_init()

    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)

    self._layout = layout
    for name, config in layout.iteritems():
      for point in ['pin', 'default']:
        Outputs._raise_if_not_in(point, config)

      self._conigure_output(name, config)

  def _conigure_output(self, name, configuration):
    pin = configuration['pin']

    self.log().debug('Pin %d -> %s' % (pin, name))

    GPIO.setup(pin, GPIO.OUT)

    if 'invert_logic' in configuration and configuration['invert_logic']:
      set_pin = lambda self,value: GPIO.output(pin, not value)
    else:
      set_pin = lambda self,value: GPIO.output(pin, value)

    set_pin(None, configuration['default'])

    setattr(self, name, MethodType(set_pin, self, type(self)))

  @staticmethod
  def _raise_if_not_in(point, config):
    if point not in config:
      raise Exception('Missing required configuration point %s' % point)

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    pass