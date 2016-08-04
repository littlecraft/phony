import time
import glib
import dbus

from phony.base.log import ClassLogger, ScopedLogger, Levels

class State:
  START = 0
  WAITING_FOR_MODEM_APPEARANCE = 1
  WAITING_FOR_MODEM_ONLINE = 2
  MODEM_IS_ONLINE = 3

  _state = START

  audio_gateway_ready_listener = None
  modem = None
  adapter = None
  device = None

  def __init__(self, next_state = START):
    self._state = next_state

  def is_at_start(self):
    return self._state == State.START

  def is_waiting_for_modem_online(self):
    return self._state == State.WAITING_FOR_MODEM_ONLINE

  def is_waiting_for_modem_appearance(self):
    return self._state == State.WAITING_FOR_MODEM_APPEARANCE

  def is_modem_online(self):
    return self._state == State.MODEM_IS_ONLINE

  def must_be(self, *one_of):
    if self._state in one_of:
      return True
    raise Exception('Internal error: State %s is unexpected' % self)

  def __repr__(self):
    if self._state == State.START:
      return 'START'
    elif self._state == State.WAITING_FOR_MODEM_APPEARANCE:
      return 'WAITING_FOR_MODEM_APPEARANCE'
    elif self._state == State.WAITING_FOR_MODEM_ONLINE:
      return 'WAITING_FOR_MODEM_ONLINE'
    elif self._state == State.MODEM_IS_ONLINE:
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

  _bus = None
  _manager = None

  _state = State.start()

  def __init__(self, bus):
    ClassLogger.__init__(self)

    self._bus = bus.system_bus()

  @ClassLogger.TraceAs.call()
  def start(self):
    self._manager = dbus.Interface(
      self._bus.get_object(self.SERVICE_NAME, '/'),
      self.MANAGER_INTERFACE
    )

  @ClassLogger.TraceAs.call()
  def stop(self):
    self._transition_to(State.start())

  @ClassLogger.TraceAs.call()
  def cancel_pending_operations(self):
    self._transition_to(State.start())

  @ClassLogger.TraceAs.call()
  def attach_audio_gateway(self, adapter, device, listener):

    path, properties = self._find_child_hfp_modem(adapter, device)

    if path:
      modem = dbus.Interface(
        self._bus.get_object(self.SERVICE_NAME, path),
        self.MODEM_INTERFACE
      )

      if properties['Online']:
        self._transition_to(State.modem_came_online(modem, listener))
      else:
        self._transition_to(State.modem_found(modem, listener))
    else:
      self._transition_to(State.modem_not_found(adapter, device, listener))

  def _transition_to(self, new_state):
    self.log().debug('State %s -> %s' % (self._state, new_state))

    previous_state = self._state
    self._state = new_state

    try:
      if new_state.is_waiting_for_modem_appearance():
        previous_state.must_be(State.START)

        self._manager.connect_to_signal('ModemAdded', self._modem_found)

      elif new_state.is_waiting_for_modem_online():
        previous_state.must_be(State.START, State.WAITING_FOR_MODEM_APPEARANCE)

        new_state.modem.connect_to_signal('PropertyChanged', self._modem_online)

      elif new_state.is_modem_online():
        previous_state.must_be(
          State.START,
          State.WAITING_FOR_MODEM_APPEARANCE,
          State.WAITING_FOR_MODEM_ONLINE
        )

        ag = OfonoHfpAg(new_state.modem.object_path, self._bus)
        new_state.audio_gateway_ready_listener(ag)

        self._transition_to(State.start())

      elif new_state.is_at_start():
        pass

      else:
        self._state = previous_state
        raise Exception('Invalid state: ' % new_state)

    except Exception, ex:
      self.log().error('Error in state transition %s -> %s:  %s' % (previous_state, new_state, ex))

  @ClassLogger.TraceAs.call()
  def _modem_found(self, path, properties):
    if self._state.is_waiting_for_modem_appearance():
      if Ofono._is_child_hfp_modem(self._state.adapter, self._state.device, path, properties):
        modem = dbus.Interface(
          self._bus.get_object(self.SERVICE_NAME, path),
          self.MODEM_INTERFACE
        )

        if properties['Online']:
          self._transition_to(
            State.modem_came_online(
              modem,
              self._state.audio_gateway_ready_listener
            )
          )
        else:
          self._transition_to(
            State.modem_found(
              modem,
              self._state.audio_gateway_ready_listener
            )
          )

  def _modem_online(self, name, value):
    if self._state.is_waiting_for_modem_online():
      if name == 'Online' and value:
        with ScopedLogger(self, '_modem_online %s' % name):
          self._transition_to(
            State.modem_came_online(
              self._state.modem,
              self._state.audio_gateway_ready_listener
            )
          )

  def _find_child_hfp_modem(self, adapter, device):
    found_path = None
    found_properties = None

    modems = self._manager.GetModems()

    for path, properties in modems:
      if Ofono._is_child_hfp_modem(adapter, device, path, properties):
        found_path = path
        found_properties = properties
        break

    return (found_path, found_properties)

  @staticmethod
  def _is_child_hfp_modem(adapter, device, path, properties):
    # TODO: Verify that the modem is attached to _both_
    # the adapter and remote device.  This is necessary
    # in cases where the host has more than one BT adapter.

    path = path.replace('_', ':')
    path = path.upper()
    return path.endswith(device.address()) \
      and properties['Type'] == 'hfp'

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    pass

class OfonoHfpAg(ClassLogger):
  _path = None
  _hfp = None
  _voice_call_manager = None

  def __init__(self, path, bus):
    ClassLogger.__init__(self)

    self._bus = bus
    self._path = path

    self._hfp = dbus.Interface(
      self._bus.get_object(Ofono.SERVICE_NAME, self._path),
      Ofono.HFP_INTERFACE
    )

    self._voice_call_manager = dbus.Interface(
      self._bus.get_object(Ofono.SERVICE_NAME, self._path),
      Ofono.VOICE_CALL_MANAGER_INTERFACE
    )

    self._voice_call_manager.connect_to_signal('CallAdded', self._call_added)
    self._voice_call_manager.connect_to_signal('CallRemoved', self._call_removed)

    self._show_properties()

  @ClassLogger.TraceAs.call()
  def dispose(self):
    try:
      self.hangup()
    except Exception, ex:
      self.log().warn(str(ex))

  def provides_voice_recognition(self):
    return 'voice-recognition' in self._hfp.GetProperties()['Features']

  @ClassLogger.TraceAs.event()
  def hangup(self):
    self._voice_call_manager.HangupAll()

  @ClassLogger.TraceAs.event()
  def begin_voice_dial(self):
    if not self.provides_voice_recognition():
      raise Exception('Device does not support voice recognition')

    self._hfp.SetProperty('VoiceRecognition', True)

  @ClassLogger.TraceAs.event()
  def dial(self, number):
    self._voice_call_manager.Dial(number, 'default')

  @ClassLogger.TraceAs.call()
  def _call_added(self, path, properties):
    pass

  @ClassLogger.TraceAs.call()
  def _call_removed(self, path):
    pass

  def _show_properties(self):
    properties = self._hfp.GetProperties()

    features = ''
    for feature in properties['Features']:
      features += feature + ' '
    self.log().info('Device HFP Features: %s' % features)

  def __repr__(self):
    info = 'Path: %s\n' % self._path

    properties = self._hfp.GetProperties()
    features = 'Features: '
    for feature in properties['Features']:
      features += feature + ' '

    info += features
    return info