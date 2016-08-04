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
      'event': [
        # Outgoing call events
        {'name': 'outgoing_call',   'src': 'idle',       'dst': 'call began'},
        {'name': 'hang_up',         'src': 'call began', 'dst': 'call ended'},
        {'name': 'remote_hang_up',  'src': 'call began', 'dst': 'call ended'},

        # Incoming call events
        {'name': 'incoming_call',   'src': 'idle',          'dst': 'ringing began'},
        {'name': 'answer',          'src': 'ringing began', 'dst': 'ringing ended'},
        {'name': 'remote_hang_up',  'src': 'ringing began', 'dst': 'ringing ended'},
        {'name': 'answer',          'src': 'ringing ended', 'dst': 'call began'},

        {'name': 'reset',           'src': '*',             'dst': 'idle'}
      ],
      'callbacks': {
        'onoutgoing_call': self._on_outgoing_call,
        'onhang_up': self._on_hang_up,
        'onremote_hang_up': self._on_remote_hang_up
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
  def _on_incoming_call(self, e):
    pass

  @ClassLogger.TraceAs.call()
  def _on_hang_up(self, e):
    pass

  @ClassLogger.TraceAs.call()
  def _on_remote_hang_up(self, e):
    pass

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
    if self._call and self._call.GetProperties()['State'] == 'incoming':
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

    if properties['State'] == 'incoming':
      for listener in self._on_ringing_begin_listeners:
        listener()
    elif properties['State'] == 'active':
      for listener in self._on_call_began_listeners:
        listener()

  @ClassLogger.TraceAs.call()
  def _call_removed(self, path):
    if self._call and self._call.object_path == path:
      for listener in self._on_call_ended_listeners:
        listener()

      self._call = None

  @ClassLogger.TraceAs.call()
  def _call_properties_changed(self, property, value, path = None):
    if self._call and self._call.object_path == path:
      if property == 'State':
        if value == 'incoming':
          for listener in self._on_ringing_begin_listeners:
            listener()
        elif value == 'active':
          # TODO: Only send ringing end signal if previously ringing
          for listener in self._on_ringing_end_listeners:
            listener()
          for listener in self._on_call_began_listeners:
            listener()

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