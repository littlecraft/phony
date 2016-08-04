import dbus
import gobject

from fysom import Fysom
from phony.base.log import ClassLogger, Levels

class Ofono(ClassLogger):
  SERVICE_NAME = 'org.ofono'
  MANAGER_INTERFACE = 'org.ofono.Manager'
  MODEM_INTERFACE = 'org.ofono.Modem'
  HFP_INTERFACE = 'org.ofono.Handsfree'
  VOICE_CALL_MANAGER_INTERFACE = 'org.ofono.VoiceCallManager'
  VOICE_CALL_INTERFACE = 'org.ofono.VoiceCall'

  POLL_FOR_HFP_MODEM_FREQUENCY_MS = 1000

  _bus = None
  _manager = None

  _poll_for_child_hfp_modem_id = None

  def __init__(self, bus_provider):
    ClassLogger.__init__(self)

    self._bus = bus_provider.system_bus()

  @ClassLogger.TraceAs.call()
  def start(self):
    self._manager = dbus.Interface(
      self._bus.get_object(self.SERVICE_NAME, '/'),
      self.MANAGER_INTERFACE
    )

  @ClassLogger.TraceAs.call()
  def stop(self):
    self._reset()

  @ClassLogger.TraceAs.call()
  def attach_audio_gateway(self, adapter, device, listener):
    self._poll_for_child_hfp_modem_id = gobject.timeout_add(
      self.POLL_FOR_HFP_MODEM_FREQUENCY_MS,
      self._poll_for_child_hfp_modem,
      adapter,
      device,
      listener
    )

  @ClassLogger.TraceAs.call()
  def cancel_pending_operations(self):
    self._reset()

  @ClassLogger.TraceAs.call()
  def _poll_for_child_hfp_modem(self, adapter, device, listener):
    path = self._find_child_hfp_modem(adapter, device)

    if path:
      ag = OfonoHfpAg(path, self._bus)
      listener(ag)

      # False: stop checking
      self._poll_for_child_hfp_modem_id = None
      return False
    else:
      # True: keep periodically checking
      return True

  def _find_child_hfp_modem(self, adapter, device):
    modems = self._manager.GetModems()

    for path, properties in modems:
      if Ofono._is_child_of(adapter, path) \
        and Ofono._is_bound_to(device, path) \
        and self._provides_hfp_interface(path):

        return path

    return None

  def _reset(self):
    if self._find_child_hfp_modem:
      try:
        gobject.source_remove(self._poll_for_child_hfp_modem_id)
      except:
        pass

      self._poll_for_child_hfp_modem_id = None

  @staticmethod
  def _is_child_of(adapter, path):
    path = path.lower()
    parent = '/org/bluez/%s' % adapter.hci_id().lower()
    return parent in path

  @staticmethod
  def _is_bound_to(device, path):
    path = path.replace('_', ':').lower()
    endpoint = device.address().lower()
    return path.endswith(endpoint)

  def _provides_hfp_interface(self, path):
    modem = dbus.Interface(
      self._bus.get_object(self.SERVICE_NAME, path),
      self.MODEM_INTERFACE
    )

    properties = modem.GetProperties()

    return self.HFP_INTERFACE in properties['Interfaces']

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    self._reset()
    self._bus = None
    self._manager = None

class OfonoHfpAg(ClassLogger):
  _path = None
  _hfp = None
  _voice_call_manager = None
  _call = None

  _on_ringing_begin_listeners = []
  _on_ringing_end_listeners = []
  _on_call_began_listeners = []
  _on_call_ended_listeners = []

  _state = None

  def __init__(self, path, bus):
    ClassLogger.__init__(self)

    self._state = Fysom({
      'initial': 'idle',
      'events': [
        # Incoming call event transitions
        {'name': 'incoming',  'src': 'idle',          'dst': 'ringing'},
        {'name': 'active',    'src': 'ringing',       'dst': 'call started'},
        {'name': 'hungup',    'src': 'ringing',       'dst': 'call ended'},

        # Outgoing call event transitions
        {'name': 'active',    'src': 'idle',          'dst': 'call started'},

        # Active call event transitions
        {'name': 'hungup',    'src': 'call started',  'dst': 'call ended'},
        {'name': 'reset',     'src': '*',             'dst': 'idle'}
      ],
      'callbacks': {
        'onchangestate': self._on_change_state,
        'onincoming': self._on_incoming,
        'onactive': self._on_active,
        'onhungup': self._on_hungup,
        'onreset': self._on_reset
      }
    })

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

    self._bus.add_signal_receiver(
      self._call_properties_changed,
      dbus_interface = Ofono.VOICE_CALL_INTERFACE,
      signal_name = 'PropertyChanged',
      path_keyword = 'path'
    )

    self._show_properties()

  @ClassLogger.TraceAs.call()
  def dispose(self):
    try:
      self.hangup()

      self._on_ringing_begin_listeners = []
      self._on_ringing_end_listeners = []
      self._on_call_began_listeners = []
      self._on_call_ended_listeners = []

    except Exception, ex:
      self.log().warn(str(ex))

  def on_ringing_begin(self, listener):
    self._on_ringing_begin_listeners.append(listener)

  def on_ringing_end(self, listener):
    self._on_ringing_end_listeners.append(listener)

  def on_call_begin(self, listener):
    self._on_call_began_listeners.append(listener)

  def on_call_end(self, listener):
    self._on_call_ended_listeners.append(listener)

  def provides_voice_recognition(self):
    return 'voice-recognition' in self._hfp.GetProperties()['Features']

  @ClassLogger.TraceAs.event(log_level = Levels.INFO)
  def answer(self):
    if self._call and self._state.isstate('ringing'):
      self._call.Answer()

  @ClassLogger.TraceAs.event(log_level = Levels.INFO)
  def hangup(self):
    self._voice_call_manager.HangupAll()

  @ClassLogger.TraceAs.event(log_level = Levels.INFO)
  def begin_voice_dial(self):
    if not self.provides_voice_recognition():
      raise Exception('Device does not support voice recognition')

    self._hfp.SetProperty('VoiceRecognition', True)

  @ClassLogger.TraceAs.event(log_level = Levels.INFO)
  def dial(self, number):
    self._voice_call_manager.Dial(number, 'default')

  @ClassLogger.TraceAs.call()
  def _call_added(self, path, properties):
    self._call = dbus.Interface(
      self._bus.get_object(Ofono.SERVICE_NAME, path),
      Ofono.VOICE_CALL_INTERFACE
    )

    if properties['State'] in ['incoming', 'active']:
      self._state.trigger(properties['State'])

  @ClassLogger.TraceAs.call()
  def _call_removed(self, path):
    if self._call and self._call.object_path == path:
      self._state.hungup()

  @ClassLogger.TraceAs.call()
  def _call_properties_changed(self, property, value, path = None):
    if self._call and self._call.object_path == path:
      if property == 'State' and value in ['incoming', 'active']:
        self._state.trigger(value)

  def _on_change_state(self, e):
    self.log().debug('Transition "%s": %s -> %s' % (e.event, e.src, e.dst))

  def _on_incoming(self, e):
    for listener in self._on_ringing_begin_listeners:
      listener()

  def _on_active(self, e):
    if e.src == 'ringing':
      for listener in self._on_ringing_end_listeners:
        listener()

    for listener in self._on_call_began_listeners:
      listener()

  def _on_hungup(self, e):
    if e.src == 'ringing':
      for listener in self._on_ringing_end_listeners:
        listener()

    for listener in self._on_call_ended_listeners:
      listener()

    self._state.reset()

  def _on_reset(self, e):
    self._call = None

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