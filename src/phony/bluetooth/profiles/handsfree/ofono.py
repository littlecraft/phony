import dbus
import dbus.service
import time
import glib

from phony.base.log import ClassLogger, ScopedLogger, Levels

class State:
  START = 0
  WAITING_FOR_MODEM_APPEARANCE = 1
  WAITING_FOR_MODEM_ONLINE = 2
  MODEM_IS_ONLINE = 3

  __state = START

  audio_gateway_ready_listener = None
  modem = None
  adapter = None
  device = None

  def __init__(self, next_state = START):
    self.__state = next_state

  def is_at_start(self):
    return self.__state == State.START

  def is_waiting_for_modem_online(self):
    return self.__state == State.WAITING_FOR_MODEM_ONLINE

  def is_waiting_for_modem_appearance(self):
    return self.__state == State.WAITING_FOR_MODEM_APPEARANCE

  def is_modem_online(self):
    return self.__state == State.MODEM_IS_ONLINE

  def must_be(self, *one_of):
    if self.__state in one_of:
      return True
    raise Exception('Internal error: State %s is unexpected' % self)

  def __repr__(self):
    if self.__state == State.START:
      return 'START'
    elif self.__state == State.WAITING_FOR_MODEM_APPEARANCE:
      return 'WAITING_FOR_MODEM_APPEARANCE'
    elif self.__state == State.WAITING_FOR_MODEM_ONLINE:
      return 'WAITING_FOR_MODEM_ONLINE'
    elif self.__state == State.MODEM_IS_ONLINE:
      return 'MODEM_IS_ONLINE'

  @staticmethod
  def start():
    return State()

  @staticmethod
  def modem_found(modem, audio_gateway_ready_listener):
    new_state = State(State.WAITING_FOR_MODEM_ONLINE)
    new_state.modem = modem
    new_state.audio_gateway_ready_listener = audio_gateway_ready_listener
    return new_state

  @staticmethod
  def modem_not_found(adapter, device, audio_gateway_ready_listener):
    new_state = State(State.WAITING_FOR_MODEM_APPEARANCE)
    new_state.device = device
    new_state.adapter = adapter
    new_state.audio_gateway_ready_listener = audio_gateway_ready_listener
    return new_state

  @staticmethod
  def modem_came_online(modem, audio_gateway_ready_listener):
    new_state = State(State.MODEM_IS_ONLINE)
    new_state.modem = modem
    new_state.audio_gateway_ready_listener = audio_gateway_ready_listener
    return new_state

class Ofono(ClassLogger):
  SERVICE_NAME = 'org.ofono'
  MANAGER_INTERFACE = 'org.ofono.Manager'
  HFP_INTERFACE = 'org.ofono.Handsfree'
  MODEM_INTERFACE = 'org.ofono.Modem'
  VOICE_CALL_MANAGER_INTERFACE = 'org.ofono.VoiceCallManager'

  __bus = None
  __manager = None

  __state = State.start()

  def __init__(self, bus):
    ClassLogger.__init__(self)

    self.__bus = bus.system_bus()

  @ClassLogger.TraceAs.call()
  def start(self):
    self.__manager = dbus.Interface(
      self.__bus.get_object(self.SERVICE_NAME, '/'),
      self.MANAGER_INTERFACE
    )

  @ClassLogger.TraceAs.call()
  def stop(self):
    self.transition_to(State.start())

  @ClassLogger.TraceAs.call()
  def cancel_pending_operations(self):
    self.transition_to(State.start())

  @ClassLogger.TraceAs.call()
  def attach_audio_gateway(self, adapter, device, listener):

    path, properties = self.__find_child_hfp_modem(adapter, device)

    if path:
      modem = dbus.Interface(
        self.__bus.get_object(self.SERVICE_NAME, path),
        self.MODEM_INTERFACE
      )

      if properties['Online']:
        self.transition_to(State.modem_came_online(modem, listener))
      else:
        self.transition_to(State.modem_found(modem, listener))
    else:
      self.transition_to(State.modem_not_found(adapter, device, listener))

  def transition_to(self, new_state):
    self.log().debug('State %s -> %s' % (self.__state, new_state))

    previous_state = self.__state
    self.__state = new_state

    try:
      if new_state.is_waiting_for_modem_appearance():
        previous_state.must_be(State.START)

        self.__manager.connect_to_signal('ModemAdded', self.__modem_found)

      elif new_state.is_waiting_for_modem_online():
        previous_state.must_be(State.START, State.WAITING_FOR_MODEM_APPEARANCE)

        new_state.modem.connect_to_signal('PropertyChanged', self.__modem_online)

      elif new_state.is_modem_online():
        previous_state.must_be(
          State.START,
          State.WAITING_FOR_MODEM_APPEARANCE,
          State.WAITING_FOR_MODEM_ONLINE
        )

        ag = OfonoHfpAg(new_state.modem.object_path, self.__bus)
        new_state.audio_gateway_ready_listener(ag)

        self.transition_to(State.start())
      elif new_state.is_at_start():
        pass

      else:
        self.__state = previous_state
        raise Exception('Invalid state: ' % new_state)

    except Exception, ex:
      self.log().error('Invalid state transition: %s -> %s' % (previous_state, new_state))

  @ClassLogger.TraceAs.event()
  def __modem_found(self, path, properties):
    if self.__state.is_waiting_for_modem_appearance():
      if Ofono.__is_child_hfp_modem(self.__state.adapter, self.__state.device, path, properties):
        modem = dbus.Interface(
          self.__bus.get_object(self.SERVICE_NAME, path),
          self.MODEM_INTERFACE
        )

        if properties['Online']:
          self.transition_to(
            State.modem_came_online(
              modem,
              self.__state.audio_gateway_ready_listener
            )
          )
        else:
          self.transition_to(
            State.modem_found(
              modem,
              self.__state.audio_gateway_ready_listener
            )
          )

  def __modem_online(self, name, value):
    if self.__state.is_waiting_for_modem_online():
      if name == 'Online' and value:
        self.transition_to(
          State.modem_came_online(
            self.__state.modem,
            self.__state.audio_gateway_ready_listener
          )
        )

  def __find_child_hfp_modem(self, adapter, device):
    found_path = None
    found_properties = None

    modems = self.__manager.GetModems()

    for path, properties in modems:
      if Ofono.__is_child_hfp_modem(adapter, device, path, properties):
        found_path = path
        found_properties = properties
        break

    return (found_path, found_properties)

  @staticmethod
  def __is_child_hfp_modem(adapter, device, path, properties):
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

  def __repr__(self):
    info = 'Path: %s\n' % self.__path

    properties = self.__hfp.GetProperties()
    features = 'Features: '
    for feature in properties['Features']:
      features += feature + ' '

    info += features
    return info