import dbus
import time

from dbus import service
from phony.base import execute
from phony.base.log import ClassLogger, ScopedLogger, Levels

class Headset(ClassLogger, dbus.service.Object):
  OBJECT_PATH = '/org/littlecraft/Phony'
  SERVICE_NAME = 'org.littlecraft.Phony'

  _started = False
  _bus = None

  _adapter = None
  _hfp = None

  _device = None
  _hfp_audio_gateway = None

  def __init__(self, bus, adapter, hfp):
    ClassLogger.__init__(self)

    self._bus = bus.session_bus()
    self._bus.request_name(self.SERVICE_NAME)
    bus_name = dbus.service.BusName(self.SERVICE_NAME, bus = self._bus)
    dbus.service.Object.__init__(self, bus_name, self.OBJECT_PATH)

    self._adapter = adapter
    self._hfp = hfp

    adapter.on_device_connected(self.device_connected)
    adapter.on_device_disconnected(self.device_disconnected)

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    self.stop()

  @ClassLogger.TraceAs.call(with_arguments = False)
  def start(self, name, pincode):
    if self._started:
      return

    self.enable()
    self._hfp.start()
    self._adapter.start(name, pincode)

  def stop(self):
    if self._started:
      self._adapter.stop()
      self._hfp.stop()
      self._reset()

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

  @ClassLogger.TraceAs.event(log_level = Levels.INFO)
  def device_connected(self, device):

    if self._device and device != self._device:
      self.log().info('One device connection allowed.  Disconnecting from previous "%s"' % self._device)
      self._reset()

    self._device = device

    try:
      self._hfp.attach_audio_gateway(
        self._adapter,
        self._device,
        self.audio_gateway_attached
      )
    except Exception, ex:
      self.log().error('Error attaching to HFP gateway: %s' % ex)
      self._reset()

  @ClassLogger.TraceAs.event(log_level = Levels.INFO)
  def device_disconnected(self, device_path):
    if self._device and device_path == self._device.path():
      self._reset()

  @ClassLogger.TraceAs.event(log_level = Levels.INFO)
  def audio_gateway_attached(self, audio_gateway):
    self._hfp_audio_gateway = audio_gateway

  @ClassLogger.TraceAs.call()
  def _reset(self):
    try:
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
  # dbus debugging methods
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