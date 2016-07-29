import dbus
import dbus.service
import time
import glib
from handset.base.log import ClassLogger, ScopedLogger, Levels

class Ofono(ClassLogger):
  SERVICE_NAME = 'org.ofono'
  MANAGER_INTERFACE = 'org.ofono.Manager'
  HFP_INTERFACE = 'org.ofono.Handsfree'
  HFP_AUDIO_MANAGER_INTERFACE = 'org.ofono.HandsfreeAudioManager'
  HFP_AUDIO_CARD = 'org.ofono.HandsfreeAudioCard'

  AUDIO_AGENT_PATH = '/phony/agent/audio'

  __bus = None

  __manager = None
  __hfp_audio_manager = None
  __hfp = None
  __audio_card = None
  __audio_agent = None

  __modem = None
  __path = None

  __attachement_attempt_listeners = []
  __attached_listeners = []
  __detached_listeners = []

  def __init__(self, bus):
    ClassLogger.__init__(self)

    self.__bus = bus.system_bus()

  @ClassLogger.TraceAs.call()
  def start(self):
    self.__manager = dbus.Interface(
      self.__bus.get_object(self.SERVICE_NAME, '/'),
      self.MANAGER_INTERFACE
    )

    self.__hfp_audio_manager = dbus.Interface(
      self.__bus.get_object(self.SERVICE_NAME, '/'),
      self.HFP_AUDIO_MANAGER_INTERFACE
    )

    #self.__audio_agent = AudioAgent(self.__bus, self.AUDIO_AGENT_PATH)

  @ClassLogger.TraceAs.call()
  def stop(self):
    pass

  @ClassLogger.TraceAs.call()
  def attach(self, adapter, device_address):
    found_path, found_properties = self.__find_modem(adapter, device_address)

    if not found_path:
      raise Exception('Unable to find HandsFree profile for ' + \
        device_address)

    self.log().info('Attempting to attach to profile path: ' + found_path)
    self.__hfp = dbus.Interface(
      self.__bus.get_object(self.SERVICE_NAME, found_path),
      self.HFP_INTERFACE
    )

    self.__show_device_properties(found_properties)
    self.__show_hands_free_properties(self.__hfp.GetProperties())

    for listener in self.__attachement_attempt_listeners:
      try:
        listener(self)
      except Exception, ex:
        raise Exception('Profile rejected for ' + \
          device_address + ': ' + str(ex))

    self.__audio_card = self.__find_audio_card(found_path)
    self.__show_audio_card_properties(self.__audio_card.GetProperties())

    self.__path = found_path

    for listener in self.__attached_listeners:
      listener(self)

  @ClassLogger.TraceAs.event()
  def detach(self, adapter, device_address):
    if not self.__path:
      return

    for listener in self.__detached_listeners:
      listener(self)

  def attached(self):
    return bool(self.__path)

  def provides_voice_recognition(self):
    if not self.attached():
      raise Exception('Profile is not attached to device')

    return 'voice-recognition' in self.__hfp.GetProperties()['Features']

  @ClassLogger.TraceAs.event()
  def begin_voice_dial(self):
    if not self.attached():
      raise Exception('Profile is not attached to device')

    if not self.provides_voice_recognition():
      raise Exception('Device does not support voice recognition')

    self.__hfp.SetProperty('VoiceRecognition', True)

  def cancel_voice_dial(self):
    if not self.attached():
      raise Exception('Profile is not attached to device')

    if not self.provides_voice_recognition():
      raise Exception('Device does not support voice recognition')

    self.__hfp.SetProperty('VoiceRecognition', False)

  @ClassLogger.TraceAs.event()
  def dial(self, number):
    if not self.attached():
      raise Exception('Profile is not attached to device')

    vcm = dbus.Interface(
      self.__bus.get_object('org.ofono', self.__path),
      'org.ofono.VoiceCallManager'
    )
    dial_path = vcm.Dial(number, 'default')

  def on_attachement_attempt(self, listener):
    self.__attachement_attempt_listeners.append(listener)

  def on_attached(self, listener):
    self.__attached_listeners.append(listener)

  def on_detached(self, listener):
    self.__detached_listeners.append(listener)

  def __find_modem(self, adapter, device_address):
    found_path = None
    found_properties = None

    modems = self.__manager.GetModems()

    for path, properties in modems:
      if path.endswith(device_address) \
         and properties['Type'] == 'hfp' \
         and self.HFP_INTERFACE in properties['Interfaces']:
        found_path = path
        found_properties = properties
        break

    return (found_path, found_properties)

  def __find_audio_card(self, device_address):
    device_address = device_address.replace('_', ':')
    for card_path, properties in self.__hfp_audio_manager.GetCards():
      if device_address.endswith(properties['RemoteAddress']):
        card = dbus.Interface(
          self.__bus.get_object(self.SERVICE_NAME, card_path),
          self.HFP_AUDIO_CARD
        )

        return card

    raise Exception('Could not find hands free audio gateway for: ' + \
      device_address)

  def __show_device_properties(self, properties):
    self.log().info('Device Name: ' + properties['Name'])
    self.log().info('Device Profile Type: ' + properties['Type'])
    self.log().info('Device Online: %s' % properties['Online'])

    ifaces = ''
    for iface in properties['Interfaces']:
      ifaces += iface + ' '
    self.log().info('Device Interfaces: %s' % ifaces)

  def __show_hands_free_properties(self, properties):
    features = ''
    for feature in properties['Features']:
      features += feature + ' '
    self.log().info('Device HFP Features: %s' % features)

  def __show_audio_card_properties(self, properties):
    self.log().info('Audio Card LocalAddress: ' + str(properties['LocalAddress']))
    self.log().info('Audio Card RemoteAddress: ' + str(properties['RemoteAddress']))
    #self.log().info('Audio Card Type: ' + str(properties['Type']))

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    pass

class AudioAgent(dbus.service.Object, ClassLogger):
  SERVICE_NAME = 'org.ofono'
  HFP_AUDIO_MANAGER_INTERFACE = 'org.ofono.HandsfreeAudioManager'

  CVSD_CODEC = dbus.Byte(0x01)
  MSBC_CODEC = dbus.Byte(0x02)

  def __init__(self, bus, path):
    ClassLogger.__init__(self)
    dbus.service.Object.__init__(self, bus, path)

    audio_manager = dbus.Interface(
      bus.get_object(self.SERVICE_NAME, '/'),
      self.HFP_AUDIO_MANAGER_INTERFACE
    )

    codecs = [
      self.CVSD_CODEC,
      self.MSBC_CODEC
    ]

    audio_manager.Register(path, codecs)

  @dbus.service.method('org.ofono.HandsfreeAudioAgent', in_signature = 'ohy')
  def NewConnection(self, card, sco, codec):
    self.log().info('NewConnection: %s, %s' % (card, sco))

    glib.io_add_watch(
      sco,
      glib.IO_IN | glib.IO_ERR | glib.IO_HUB,
      self.__io_watch
    )

  @dbus.service.method('org.ofono.HandsfreeAudioAgent')
  def Release(self):
    self.log().info('Release')

  def __io_watch(self, fd, condition):
    events = []

    if condition & glib.IO_ERR:
      events.append('Error')

    if condition & glib.IO_HUP:
      events.append('Closed')

    if condition & glib.IO_IN:
      events.append('Read')

    self.log().debug('IO Events: ' + events.join(','))