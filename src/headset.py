import dbus
import time

from dbus import service
from phony.base import execute
from phony.base.log import ClassLogger, ScopedLogger, Levels

class Headset(ClassLogger, dbus.service.Object):
  OBJECT_PATH = '/org/littlecraft/Phony'
  SERVICE_NAME = 'org.littlecraft.Phony'

  __started = False
  __bus = None

  __adapter = None
  __profile = None

  __device = None
  __audio_gateway = None

  def __init__(self, bus, adapter, hfp):
    ClassLogger.__init__(self)

    self.__bus = bus.session_bus()
    self.__bus.request_name(self.SERVICE_NAME)
    bus_name = dbus.service.BusName(self.SERVICE_NAME, bus = self.__bus)
    dbus.service.Object.__init__(self, bus_name, self.OBJECT_PATH)

    self.__adapter = adapter
    self.__hfp = hfp

    adapter.on_device_connected(self.device_connected)
    adapter.on_device_disconnected(self.device_disconnected)

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    self.stop()

  @ClassLogger.TraceAs.call(with_arguments = False)
  def start(self, name, pincode):
    if self.__started:
      return

    self.enable()
    self.__hfp.start()
    self.__adapter.start(name, pincode)

  def stop(self):
    if self.__started:
      self.__adapter.stop()
      self.__hfp.stop()
      self.__reset()

  def enable(self):
    self.log().info("Enabling radio")
    try:
      self.__exec("rfkill unblock bluetooth")
    except Exception, ex:
      self.log().debug('Unable to unblock bluetooth with rfkill: %s' % ex)

  def disable(self):
    self.log().info("Disabling radio")
    try:
      self.__exec("rfkill block bluetooth")
    except:
      pass

  def enable_pairability(self, timeout = 0):
    self.__adapter.enable_pairability(timeout)

  def disable_pairability(self):
    self.__adapter.disable_pairability()

  @ClassLogger.TraceAs.event(log_level = Levels.INFO)
  def device_connected(self, device):

    if self.__device and device != self.__device:
      self.log().info('One device connection allowed.  Disconnecting from previous "%s"' % self.__device)
      self.__reset()

    self.__device = device

    try:
      self.__hfp.attach_audio_gateway(
        self.__adapter,
        self.__device,
        self.audio_gateway_attached
      )
    except Exception, ex:
      self.log().error('Error attaching to HFP gateway: %s' % ex)
      self.__reset()

  @ClassLogger.TraceAs.event(log_level = Levels.INFO)
  def device_disconnected(self, device_path):
    if self.__device and device_path == self.__device.path():
      self.__reset()

  @ClassLogger.TraceAs.event(log_level = Levels.INFO)
  def audio_gateway_attached(self, audio_gateway):
    self.__audio_gateway = audio_gateway

  @ClassLogger.TraceAs.call()
  def __reset(self):
    try:
      self.__adapter.cancel_pending_operations()
      self.__hfp.cancel_pending_operations()

      if self.__audio_gateway:
        self.__audio_gateway.dispose()
        self.__audio_gateway = None

      if self.__device:
        self.__device.dispose()
        self.__device = None
    except Exception, ex:
      self.log().warn('Reset error: %s' % ex)

  def __exec(self, command):
    self.log().debug('Running: ' + command)
    execute.privileged(command, shell = True)

  #
  # dbus debugging methods
  #

  @dbus.service.method(dbus_interface = SERVICE_NAME)
  def BeginVoiceDial(self):
    if self.__audio_gateway:
      self.__audio_gateway.begin_voice_dial()
    else:
      raise Exception('No audio gateway is connected')

  @dbus.service.method(dbus_interface = SERVICE_NAME,
    input_signature = 's')
  def Dial(self, number):
    if self.__audio_gateway:
      self.__audio_gateway.dial(number)
    else:
      raise Exception('No audio gateway is connected')

  @dbus.service.method(dbus_interface = SERVICE_NAME)
  def HangUp(self):
    if self.__audio_gateway:
      self.__audio_gateway.hangup()
    else:
      raise Exception('No audio gateway is connected')

  @dbus.service.method(dbus_interface = SERVICE_NAME)
  def Reset(self):
    self.__reset()

  @dbus.service.method(dbus_interface = SERVICE_NAME, out_signature = 's')
  def GetStatus(self):
    status = ''

    if self.__adapter:
      status += 'Adapter:\n%s\n\n' % self.__adapter
    if self.__device:
      status += 'Device:\n%s\n\n' % self.__device
    if self.__audio_gateway:
      status += 'AG:\n%s\n\n' % self.__audio_gateway

    return status