import dbus

from dbus import service
from phony.base.log import ClassLogger

class DbusDebugInterface(ClassLogger, dbus.service.Object):

  OBJECT_PATH = '/org/littlecraft/Phony'
  SERVICE_NAME = 'org.littlecraft.Phony'

  _bus = None
  _headset = None

  def __init__(self, bus_provider, headset):
    ClassLogger.__init__(self)

    self._headset = headset

    self._bus = bus_provider.session_bus()

    self._bus.request_name(self.SERVICE_NAME)
    bus_name = dbus.service.BusName(self.SERVICE_NAME, bus = self._bus)
    dbus.service.Object.__init__(self, bus_name, self.OBJECT_PATH)

  @dbus.service.method(dbus_interface = SERVICE_NAME)
  def BeginVoiceDial(self):
    self._headset.begin_voice_dial()

  @dbus.service.method(dbus_interface = SERVICE_NAME,
    input_signature = 's')
  def Dial(self, number):
    self._headset.dial(number)

  @dbus.service.method(dbus_interface = SERVICE_NAME)
  def Answer(self):
    self._headset.answer()

  @dbus.service.method(dbus_interface = SERVICE_NAME)
  def HangUp(self):
    self._headset.hangup()

  @dbus.service.method(dbus_interface = SERVICE_NAME)
  def Mute(self):
    self._headset.mute_microphone()

  @dbus.service.method(dbus_interface = SERVICE_NAME)
  def Unmute(self):
    self._headset.unmute_microphone()

  @dbus.service.method(dbus_interface = SERVICE_NAME,
    input_signature = 'i')
  def SetMicrophoneVolume(self, volume):
    self._headset.set_microphone_volume(volume)

  @dbus.service.method(dbus_interface = SERVICE_NAME,
    input_signature = 'i')
  def SetSpeakerVolume(self, volume):
    self._headset.set_speaker_volume(volume)

  @dbus.service.method(dbus_interface = SERVICE_NAME)
  def Reset(self):
    self._headset.reset()

  @dbus.service.method(dbus_interface = SERVICE_NAME, out_signature = 'a{ss}')
  def GetStatus(self):
    return self._headset.get_status()

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    pass