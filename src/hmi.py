from fysom import Fysom
from phony.base.log import ClassLogger

class HandCrankTelephoneControls(ClassLogger):
  ENCODER_PULSES_TO_INTITATE_CALL = 8

  _inputs = None
  _ringer = None
  _headset = None

  _encoder_pulse_count = 0
  _state = None

  def __init__(self, io_inputs, bell_ringer, headset):
    ClassLogger.__init__(self)

    self._state = Fysom({
      'initial': 'idle',
      'events': [
        {'name': 'off_hook',          'src': '*',       'dst': 'ready'},
        {'name': 'hand_crank_pulsed', 'src': 'ready',   'dst': '='},
        {'name': 'initiate_call',     'src': 'ready',   'dst': 'call_initiated'},
        {'name': 'on_hook',           'src': '*',       'dst': 'idle'},
        {'name': 'hard_reset',        'src': '*',       'dst': '='}
      ],
      'callbacks': {
        'onchangestate': self._on_change_state,
        'onready': self._on_ready,
        'onoff_hook': self._on_off_hook,
        'onhand_crank_pulsed': self._on_hand_crank_pulsed,
        'oninitiate_call': self._on_initiate_call,
        'onon_hook': self._on_on_hook,
        'onhard_reset': self._on_hard_reset
      }
    })

    self._ringer = bell_ringer

    self._headset = headset
    self._headset.on_ringing_state_changed(self._on_ringing_state_changed)

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

  def _on_ready(self, e):
    self._encoder_pulse_count = 0

  def _on_off_hook(self, e):
    try:
      self._headset.answer_call()
    except Exception, ex:
      self.log().error('Error caught while answering: %s' % ex)

  def _on_on_hook(self, e):
    try:
      self._headset.hangup_call()
    except Exception, ex:
      self.log().error('Error caught while hanging up: %s' % ex)

  def _on_hand_crank_pulsed(self, e):
    self._encoder_pulse_count += 1

    self.log().variable(
      '_encoder_pulse_count',
      self._encoder_pulse_count,
      label = None
    )

    if self._encoder_pulse_count % self.ENCODER_PULSES_TO_INTITATE_CALL == 0:
      self._state.initiate_call()

  def _on_initiate_call(self, e):
    try:
      self._headset.initiate_call()
    except Exception, ex:
      self.log().error('Error caught while initiating call: %s' % ex)

  def _on_hard_reset(self, e):
    try:
      self._reset()
    except Exception, ex:
      self.log().error('Error caught while resetting: %s' % ex)

  #
  # headset callbacks
  #

  @ClassLogger.TraceAs.event()
  def _on_ringing_state_changed(self, value):
    try:
      if value:
        self._ringer.start_ringing()
      else:
        self._ringer.stop_ringing()
    except Exception, ex:
      self.log().error('Error caught while toggling ringer: %s' % ex)

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
    if self._state.can('hand_crank_pulsed'):
      self._state.hand_crank_pulsed()
    else:
      self.log().debug('Ignore crank pulse')

  @ClassLogger.TraceAs.event()
  def _rest_switch_pressed(self):
    self._state.hard_reset()

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    pass