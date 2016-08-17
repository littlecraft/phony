import dbus
import time

from dbus import service
from phony.base import execute
from phony.base.log import ClassLogger, ScopedLogger, Levels

class HandsFreeHeadset(ClassLogger, dbus.service.Object):
  """
  Behaves like a bluetooth headset, allowing only one device
  to connect/pair at a time, requiring that the device
  provide HFP and voice-dialing capabilities.
  """

  OBJECT_PATH = '/org/littlecraft/Phony'
  SERVICE_NAME = 'org.littlecraft.Phony'

  _started = False
  _bus = None

  _adapter = None
  _hfp = None
  _audio = None

  _device = None
  _hfp_audio_gateway = None

  def __init__(self, bus_provider, adapter, hfp, audio, hmi):
    ClassLogger.__init__(self)

    self._bus = bus_provider.session_bus()

    self._bus.request_name(self.SERVICE_NAME)
    bus_name = dbus.service.BusName(self.SERVICE_NAME, bus = self._bus)
    dbus.service.Object.__init__(self, bus_name, self.OBJECT_PATH)

    self._adapter = adapter
    self._hfp = hfp
    self._audio = audio

    adapter.on_device_connected(self._device_connected)
    adapter.on_device_disconnected(self._device_disconnected)

    hmi.on_initiate_call(self._initiate_call)
    hmi.on_answer(self._answer_call)
    hmi.on_hangup(self._hangup_call)
    hmi.on_hard_reset(self._hard_reset)

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    self.stop()

  @ClassLogger.TraceAs.call(with_arguments = False)
  def start(self, name, pincode):
    if self._started:
      return

    self.enable()
    self._audio.start()
    self._hfp.start()
    self._adapter.start(name, pincode)

    self._started = True

  def stop(self):
    if self._started:
      self._adapter.stop()
      self._hfp.stop()
      self._reset()

      self._started = False

  def enable(self):
    self.log().info("Enabling radio")
    try:
      self._exec("rfkill unblock bluetooth")
    except Exception, ex:
      self.log().debug('Unable to unblock bluetooth with rfkill: %s' % ex)

  def disable(self):
    self.log().info("Disabling radio")
    try:
      self._exec("rfkill block bluetooth")
    except:
      pass

  def enable_pairability(self, timeout = 0):
    self._adapter.enable_pairability(timeout)

  def disable_pairability(self):
    self._adapter.disable_pairability()

  #
  # Bluetooth adapter event callbacks
  #

  @ClassLogger.TraceAs.event(log_level = Levels.INFO)
  def _device_connected(self, device):

    if self._device and device != self._device:
      self.log().info('One device connection allowed.  Disconnecting from previous "%s"' % self._device)
      self._reset()

    self._device = device

    try:
      self._hfp.attach_audio_gateway(
        self._adapter,
        self._device,
        self._audio_gateway_attached
      )
    except Exception, ex:
      self.log().error('Error attaching to HFP gateway: %s' % ex)
      self._reset()

  @ClassLogger.TraceAs.event(log_level = Levels.INFO)
  def _device_disconnected(self, device_path):
    if self._device and device_path == self._device.path():
      self._reset()

  @ClassLogger.TraceAs.event(log_level = Levels.INFO)
  def _audio_gateway_attached(self, audio_gateway):
    if audio_gateway.provides_voice_recognition():
      self._hfp_audio_gateway = audio_gateway
      audio_gateway.on_ringing_begin(self._ringing_began)
      audio_gateway.on_ringing_end(self._ringing_ended)
      audio_gateway.on_call_begin(self._call_began)
      audio_gateway.on_call_end(self._call_ended)
    else:
      self.log().info('Device %s does not provide voice dialing. Disconnecting...')
      self._reset()

  #
  # Audio gateway event handlers:
  #

  @ClassLogger.TraceAs.event(log_level = Levels.INFO)
  def _ringing_began(self):
    pass

  @ClassLogger.TraceAs.event(log_level = Levels.INFO)
  def _ringing_ended(self):
    pass

  @ClassLogger.TraceAs.event(log_level = Levels.INFO)
  def _call_began(self):
    pass

  @ClassLogger.TraceAs.event(log_level = Levels.INFO)
  def _call_ended(self):
    pass

  #
  # Control IO gesture event handlers
  #

  @ClassLogger.TraceAs.event(log_level = Levels.INFO)
  def _answer_call(self):
    if self._hfp_audio_gateway:
      self._audio.unmute_microphone()
      self._hfp_audio_gateway.answer()

  @ClassLogger.TraceAs.event(log_level = Levels.INFO)
  def _initiate_call(self):
    if self._hfp_audio_gateway:
      self._audio.unmute_microphone()
      self._hfp_audio_gateway.begin_voice_dial()

  @ClassLogger.TraceAs.event(log_level = Levels.INFO)
  def _hangup_call(self):
    try:
      if self._hfp_audio_gateway:
        self._audio.mute_microphone()
        self._hfp_audio_gateway.hangup()
        self._hfp_audio_gateway.end_voice_dial()
    except Exception, ex:
      self.log().debug('Error caught while hanging up: %s' % ex)

  @ClassLogger.TraceAs.event(log_level = Levels.INFO)
  def _hard_reset(self):
    self._reset()

  #
  # Private methods
  #

  @ClassLogger.TraceAs.call()
  def _reset(self):
    try:
      self._audio.mute_microphone()
      self._adapter.cancel_pending_operations()
      self._hfp.cancel_pending_operations()

      if self._hfp_audio_gateway:
        self._hfp_audio_gateway.dispose()
        self._hfp_audio_gateway = None

      if self._device:
        self._device.dispose()
        self._device = None
    except Exception, ex:
      self.log().warn('Reset error: %s' % ex)

  def _exec(self, command):
    self.log().debug('Running: ' + command)
    execute.privileged(command, shell = True)

  #
  # dbus debugging interface
  #

  @dbus.service.method(dbus_interface = SERVICE_NAME)
  def BeginVoiceDial(self):
    if self._hfp_audio_gateway:
      self._hfp_audio_gateway.begin_voice_dial()
    else:
      raise Exception('No audio gateway is connected')

  @dbus.service.method(dbus_interface = SERVICE_NAME,
    input_signature = 's')
  def Dial(self, number):
    if self._hfp_audio_gateway:
      self._hfp_audio_gateway.dial(number)
    else:
      raise Exception('No audio gateway is connected')

  @dbus.service.method(dbus_interface = SERVICE_NAME)
  def Answer(self):
    if self._hfp_audio_gateway:
      self._hfp_audio_gateway.answer()
    else:
      raise Exception('No audio gateway is connected')

  @dbus.service.method(dbus_interface = SERVICE_NAME)
  def HangUp(self):
    if self._hfp_audio_gateway:
      self._hfp_audio_gateway.hangup()
    else:
      raise Exception('No audio gateway is connected')

  @dbus.service.method(dbus_interface = SERVICE_NAME)
  def Reset(self):
    self._reset()

  @dbus.service.method(dbus_interface = SERVICE_NAME, out_signature = 's')
  def GetStatus(self):
    status = ''

    if self._adapter:
      status += 'Adapter:\n%s\n\n' % self._adapter
    if self._device:
      status += 'Device:\n%s\n\n' % self._device
    if self._hfp_audio_gateway:
      status += 'AG:\n%s\n\n' % self._hfp_audio_gateway

    return status