import copy
import gobject

from phony.base.log import ClassLogger
from RPi import GPIO

class Inputs(ClassLogger):
  _layout = {}
  _inputs_by_channel = {}
  _outputs_by_channel = {}

  _rising_callback_by_channel_name = {}
  _falling_callback_by_channel_name = {}

  def __init__(self, layout):
    ClassLogger.__init__(self)

    # IO event callbacks occur in another thread
    gobject.threads_init()
    GPIO.setmode(GPIO.BCM)

    self._layout = layout
    for name, config in layout.iteritems():
      config = copy.deepcopy(config)
      config['name'] = name

      if config['direction'] == 'input':
        self._inputs_by_channel[config['pin']] = config
      else:
        self._outputs_by_channel[config['pin']] = config

    for name, config in self._inputs_by_channel.iteritems():
      self._configure_input(config)

    for name, config in self._outputs_by_channel.iteritems():
      self._configure_output(config)

  def on_rising_edge(self, channel_name, callback):
    self._rising_callback_by_channel_name[channel_name] = callback

  def on_falling_edge(self, channel_name, callback):
    self._falling_callback_by_channel_name[channel_name] = callback

  @ClassLogger.TraceAs.call()
  def _channel_changed(self, channel):
    name = self._inputs_by_channel[channel]['name']
    if GPIO.input(channel):
      self._rising_callback_by_channel_name[name]()
    else:
      self._falling_callback_by_channel_name[name]()

  def _configure_input(self, configuration):
    pin = configuration['pin']

    if configuration['polarity'] == 'pull-up':
      pull_up_or_down = GPIO.PUD_UP
    else:
      pull_up_or_down = GPIO.PUD_DOWN

    debounce = configuration['debounce']

    GPIO.setup(pin, GPIO.IN, pull_up_down = pull_up_or_down)
    GPIO.add_event_detect(pin, GPIO.BOTH, callback = self._channel_changed, bouncetime = debounce)

  def _configure_output(self, configuration):
    pass

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    for channel in self._inputs_by_channel:
      GPIO.remove_event_detect(channel)