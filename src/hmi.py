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
        {'name': 'incoming_call',     'src': 'idle',           'dst': 'call_incoming'},

        {'name': 'call_began',        'src': '*',              'dst': 'in_call'},
        {'name': 'call_ended',        'src': '*',              'dst': 'idle'},

        {'name': 'off_hook',          'src': 'call_incoming',  'dst': '='},
        {'name': 'off_hook',          'src': 'idle',           'dst': 'initiate_call'},

        {'name': 'on_hook',           'src': '*',              'dst': 'idle'}
      ],
      'callbacks': {
        'onchangestate': self._on_change_state,

        'oncall_incoming': self._on_call_incoming,
        'oncall_ended': self._on_call_ended,
        'oncall_began': self._on_call_began,

        'onoff_hook': self._on_off_hook,

        'oninitiate_call': self._on_initiate_call,

        'onon_hook': self._on_on_hook
      }
    })

    self._ringer = bell_ringer

    self._headset = headset
    self._headset.on_incoming_call(self._incoming_call)
    self._headset.on_call_began(self._call_began)
    self._headset.on_call_ended(self._call_ended)

    self._inputs = io_inputs
    self._inputs.on_rising_edge('hook_switch', self._swich_hook_high)
    self._inputs.on_falling_edge('hook_switch', self._switch_hook_low)
    self._inputs.on_pulse('hand_crank_encoder', self._encoder_pulsed)
    self._inputs.on_falling_edge('reset_switch', self._rest_switch_pressed)

  @ClassLogger.TraceAs.call()
  def _reset(self):
    self._headset.reset()
    self._ringer.stop_ringing()

  #
  # State change callbacks
  #

  def _on_change_state(self, e):
    self.log().debug('State transition "%s": %s -> %s' % (e.event, e.src, e.dst))

  def _on_call_incoming(self, e):
    try:
      self._ringer.start_ringing()
    except Exception, ex:
      self.log().error('Error caught for incoming call: %s' % ex)

  def _on_call_ended(self, e):
    try:
      if e.src == 'call_incoming':
        self._ringer.stop_ringing()
    except Exception, ex:
      self.log().error('Error caught for call ended: %s' % ex)

  def _on_call_began(self, e):
    try:
      if e.src == 'call_incoming':
        self._ringer.stop_ringing()
    except Exception, ex:
      self.log().error('Error caught for call began: %s' % ex)

  def _on_off_hook(self, e):
    try:
      if e.src == 'call_incoming':
        self._headset.answer_call()
    except Exception, ex:
      self.log().error('Error caught for off hook: %s' % ex)

  def _on_initiate_call(self, e):
    try:
      self._headset.initiate_call()
    except Exception, ex:
      self.log().error('Error caught for initiate call: %s' % ex)

  def _on_on_hook(self, e):
    try:
      self._headset.hangup_call()
    except Exception, ex:
      self.log().error('Error caught for on hook: %s' % ex)

  #
  # headset callbacks
  #

  @ClassLogger.TraceAs.event()
  def _incoming_call(self):
    self._state.incoming_call()

  @ClassLogger.TraceAs.event()
  def _call_began(self):
    self._state.call_began()

  @ClassLogger.TraceAs.event()
  def _call_ended(self):
    self._state.call_ended()

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
    pass

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    pass