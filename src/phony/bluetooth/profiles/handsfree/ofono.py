import dbus
import dbus.service
import time
import glib

from phony.base.log import ClassLogger, ScopedLogger, Levels

class State:
  START = 0
  BEGIN_ATTACH = 1
  WAITING_FOR_MODEM_ONLINE = 2
  WAITING_FOR_MODEM_APPEARANCE = 3

  __state = START

  audio_gateway_ready_listener = None
  modem = None
  adapter = None
  device = None

  def __init__(self, last = None, next_state = START):
    if last:
      self.audio_gateway_ready_listener = last.audio_gateway_ready_listener
      self.modem = last.modem
      self.adapter = last.adapter
      self.device = last.device

    self.__state = next_state

  def waiting_for_modem_online(self):
    return self.__state == State.WAITING_FOR_MODEM_ONLINE

  def waiting_for_modem_appearance(self):
    return self.__state == State.WAITING_FOR_MODEM_APPEARANCE

  @staticmethod
  def empty():
    return State()

  @staticmethod
  def begin_attach(last_state, audio_gateway_ready_listener):
    new_state = State(last_state, State.BEGIN_ATTACH)
    new_state.audio_gateway_ready_listener = audio_gateway_ready_listener
    return new_state

  @staticmethod
  def modem_found(last_state, modem):
    new_state = State(last_state, State.WAITING_FOR_MODEM_ONLINE)
    new_state.modem = modem
    return new_state

  @staticmethod
  def modem_not_found(last_state, adapter, device):
    new_state = State(last_state, State.WAITING_FOR_MODEM_APPEARANCE)
    new_state.device = device
    new_state.adapter = adapter
    return new_state

class Ofono(ClassLogger):
  SERVICE_NAME = 'org.ofono'
  MANAGER_INTERFACE = 'org.ofono.Manager'
  HFP_INTERFACE = 'org.ofono.Handsfree'
  MODEM_INTERFACE = 'org.ofono.Modem'
  VOICE_CALL_MANAGER_INTERFACE = 'org.ofono.VoiceCallManager'

  __bus = None
  __manager = None

  __state = State.empty()

  def __init__(self, bus):
    ClassLogger.__init__(self)

    self.__bus = bus.system_bus()

  @ClassLogger.TraceAs.call()
  def start(self):
    self.__manager = dbus.Interface(
      self.__bus.get_object(self.SERVICE_NAME, '/'),
      self.MANAGER_INTERFACE
    )

    self.__manager.connect_to_signal('ModemAdded', self.__modem_found)
    self.__manager.connect_to_signal('ModemRemoved', self.__modem_removed)

  @ClassLogger.TraceAs.call()
  def stop(self):
    self.__state = State.empty()

  @ClassLogger.TraceAs.call()
  def attach_audio_gateway(self, adapter, device, audio_gateway_ready_listener):

    self.__state = State.begin_attach(self.__state, audio_gateway_ready_listener)

    path, properties = self.__find_our_hfp_modem(adapter, device)

    if path:
      modem = dbus.Interface(
        self.__bus.get_object(self.SERVICE_NAME, path),
        self.MODEM_INTERFACE
      )

      self.__state = State.modem_found(self.__state, modem)

      if properties['Online']:
        self.log().debug('Found modem immediately!')

        self.__modem_is_online()
      else:
        self.log().debug('Found modem, but it is offline, waiting for it to come online')

        modem.connect_to_signal('PropertyChanged',
          self.__wait_for_modem_online)

    else:
      self.log().debug('No modem found, waiting for one to appear')

      self.__state = State.modem_not_found(self.__state, adapter, device)

  @ClassLogger.TraceAs.event()
  def __modem_found(self, path, properties):
    pass

  @ClassLogger.TraceAs.event()
  def __modem_removed(self, path):
    pass

  def __wait_for_modem_online(self, name, value):
    if self.__state.waiting_for_modem_online():
      if name == 'Online' and value:
        self.__modem_is_online()

  def __modem_is_online(self):
    self.log().debug('Modem is online, notifying...')

    ag = OfonoHfpAg(self.__state.modem.object_path, self.__bus)
    self.__state.audio_gateway_ready_listener(ag)

    self.__state = State.empty()

  def __find_our_hfp_modem(self, adapter, device):
    found_path = None
    found_properties = None

    modems = self.__manager.GetModems()

    for path, properties in modems:
      if Ofono.__is_our_hfp_modem(adapter, device, path, properties):
        found_path = path
        found_properties = properties
        break

    return (found_path, found_properties)

  @staticmethod
  def __is_our_hfp_modem(adapter, device, path, properties):
    # TODO: Verify that the modem is attached to _both_
    # the adapter and remote device.  This is necessary
    # in cases where the host has more than one BT adapter.

    path = path.replace('_', ':')
    path = path.upper()
    return path.endswith(device.address()) \
      and properties['Type'] == 'hfp'

  def __show_modem_properties(self, properties):
    self.log().info('Device Name: ' + properties['Name'])
    self.log().info('Device Profile Type: ' + properties['Type'])
    self.log().info('Device Online: %s' % properties['Online'])

    ifaces = ''
    for iface in properties['Interfaces']:
      ifaces += iface + ' '
    self.log().info('Device Interfaces: %s' % ifaces)

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    pass

class OfonoHfpAg(ClassLogger):
  __path = None
  __hfp = None
  __voice_call_manager = None

  def __init__(self, path, bus):
    ClassLogger.__init__(self)

    self.__bus = bus
    self.__path = path

    self.__hfp = dbus.Interface(
      self.__bus.get_object(Ofono.SERVICE_NAME, self.__path),
      Ofono.HFP_INTERFACE
    )

    self.__voice_call_manager = dbus.Interface(
      self.__bus.get_object(Ofono.SERVICE_NAME, self.__path),
      Ofono.VOICE_CALL_MANAGER_INTERFACE
    )

    self.__show_hands_free_properties()

  @ClassLogger.TraceAs.call()
  def dispose(self):
    try:
      self.hangup()
    except Exception, ex:
      self.log().warn(str(ex))

  def provides_voice_recognition(self):
    return 'voice-recognition' in self.__hfp.GetProperties()['Features']

  @ClassLogger.TraceAs.event()
  def hangup(self):
    self.__voice_call_manager.HangupAll()

  @ClassLogger.TraceAs.event()
  def begin_voice_dial(self):
    if not self.provides_voice_recognition():
      raise Exception('Device does not support voice recognition')

    self.__hfp.SetProperty('VoiceRecognition', True)

  @ClassLogger.TraceAs.event()
  def dial(self, number):
    self.__voice_call_manager.Dial(number, 'default')

  def __show_hands_free_properties(self):
    properties = self.__hfp.GetProperties()

    features = ''
    for feature in properties['Features']:
      features += feature + ' '
    self.log().info('Device HFP Features: %s' % features)