from fysom import Fysom
from phony.base.log import ClassLogger

class HandCrankTelephoneControls(ClassLogger):
  ENCODER_PULSES_TO_INTITATE_CALL = 8

  _inputs = None
  _ringer = None
  _headset = None

  _state = None

  def __init__(self, io_inputs, bell_ringer, headset):
    ClassLogger.__init__(self)

    self._state = Fysom({
      'initial': 'idle',
      'events': [
        #
        # Ingress calling state transitions
        #
        {'name': 'incoming_call', 'src': 'idle',            'dst': 'ringing'},
        {'name': 'call_ended',    'src': 'ringing',         'dst': 'idle'},
        {'name': 'off_hook',      'src': 'ringing',         'dst': 'in_call'},
        {'name': 'call_began',    'src': '*',               'dst': '='},

        #
        # Egress calling state transitions
        #
        {'name': 'off_hook',      'src': 'idle',            'dst': 'initiating_call'},
        {'name': 'call_began',    'src': 'initiating_call', 'dst': 'in_call'},

        #
        # In-call state transitions
        #
        {'name': 'on_hook',       'src': '*',               'dst': 'idle'},

        #
        # Ignore these transitions:
        #

        # We don't care about call's ending in any other state except while ringing
        {'name': 'call_ended',    'src': '*',               'dst': '='},
        # Incoming calls in any state other than idle, do not cause a transition
        {'name': 'incoming_call', 'src': '*',               'dst': '='},
        # Ignore off-hook switch bouncing
        {'name': 'off_hook',      'src': '*',               'dst': '='}
      ],
      'callbacks': {
        'onchangestate': self._on_change_state,

        # State transition callbacks
        'onidle': self._on_idle,
        'onringing': self._on_ringing,
        'onin_call': self._on_in_call,
        'oninitiating_call': self._on_initiating_call,

        # Event callbacks
        'onincoming_call': self._on_incoming_call
      }
    })

    self._ringer = bell_ringer

    self._headset = headset
    self._headset.on_incoming_call(self._incoming_call)
    self._headset.on_call_began(self._call_began)
    self._headset.on_call_ended(self._call_ended)
    self._headset.on_device_connected(self._device_connected)

    self._inputs = io_inputs
    self._inputs.on_rising_edge('hook_switch', self._swich_hook_high)
    self._inputs.on_falling_edge('hook_switch', self._switch_hook_low)
    self._inputs.on_pulse('hand_crank_encoder', self._encoder_pulsed)
    self._inputs.on_falling_edge('reset_switch', self._rest_switch_pressed)

  @ClassLogger.TraceAs.call()
  def _reset(self):
    self._ringer.stop_ringing()
    self._headset.reset()

  #
  # State change callbacks
  #

  def _on_change_state(self, e):
    self.log().debug('** State: %s -> <%s> -> %s' % (e.src, e.event, e.dst))

  def _on_idle(self, e):
    try:
      if e.src == 'ringing':
        self._ringer.stop_ringing()
      elif e.src == 'in_call':
        self._headset.hangup_call()
      elif e.src == 'initiating_call':
        self._headset.cancel_call_initiation()
        self._headset.hangup_call()
    except Exception, ex:
      self.log().error('Error caught while going idle: %s' % ex)

  def _on_ringing(self, e):
    try:
      self._ringer.start_ringing()
    except Exception, ex:
      self.log().error('Error caught while going ringing: %s' % ex)

  def _on_in_call(self, e):
    try:
      if e.src == 'ringing':
        self._ringer.stop_ringing()
        self._headset.answer_call()
    except Exception, ex:
      self.log().error('Error caught while going in_call: %s' % ex)

  def _on_initiating_call(self, e):
    try:
      if e.src == 'idle':
        self._headset.initiate_call()
    except Exception, ex:
      self.log().error('Error caught while going initiating_call: %s' % ex)

  def _on_incoming_call(self, e):
    try:
      if e.src != 'idle':
        self._headset.deflect_call_to_voicemail()
    except Exception, ex:
      self.log().error('Error caught for event call_began: %s' % ex)

  #
  # headset callbacks
  #

  @ClassLogger.TraceAs.event()
  def _incoming_call(self, path):
    self._state.incoming_call()

  @ClassLogger.TraceAs.event()
  def _call_began(self, path):
    self._state.call_began()

  @ClassLogger.TraceAs.event()
  def _call_ended(self, path):
    self._state.call_ended()

  @ClassLogger.TraceAs.event()
  def _device_connected(self):
    self._ringer.short_ring()

  #
  # Low-level IO callbacks
  #

  @ClassLogger.TraceAs.event()
  def _swich_hook_high(self):
    self._state.off_hook()

  @ClassLogger.TraceAs.event()
  def _switch_hook_low(self):
    self._state.on_hook()

  def _encoder_pulsed(self):
    pass
    #if self._state.can('hand_crank_pulsed'):
    #  self._state.hand_crank_pulsed()
    #else:
    #  self.log().debug('Ignore crank pulse')

  @ClassLogger.TraceAs.event()
  def _rest_switch_pressed(self):
    self._reset()

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    pass