
from fysom import Fysom
from phony.base.log import ClassLogger

class HandCrankTelephoneControls(ClassLogger):
  ENCODER_PULSES_TO_INTITATE_CALL = 8

  _inputs = None
  _headset = None

  _encoder_pulse_count = 0
  _state = None

  def __init__(self, io_inputs, headset):
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

    self._headset = headset

    self._inputs = io_inputs
    self._inputs.on_rising_edge('hook_switch', self._swich_hook_high)
    self._inputs.on_falling_edge('hook_switch', self._switch_hook_low)
    self._inputs.on_pulse('hand_crank_encoder', self._encoder_pulsed)
    self._inputs.on_falling_edge('reset_switch', self._rest_switch_pressed)

  #
  # State change callbacks
  #

  def _on_change_state(self, e):
    self.log().debug('State transition "%s": %s -> %s' % (e.event, e.src, e.dst))

  def _on_ready(self, e):
    self._encoder_pulse_count = 0

  def _on_off_hook(self, e):
    self._headset.answer_call()

  def _on_on_hook(self, e):
    self._headset.hangup_call()

  def _on_hand_crank_pulsed(self, e):
    self._encoder_pulse_count += 1

    self.log().variable(
      '_encoder_pulse_count',
      self._encoder_pulse_count,
      label = None
    )

    if self._encoder_pulse_count % TelephoneControls.ENCODER_PULSES_TO_INTITATE_CALL == 0:
      self._state.initiate_call()

  def _on_initiate_call(self, e):
    self._headset.initiate_call()

  def _on_hard_reset(self, e):
    self._headset.reset()

  #
  # Low-level IO callbacks
  #

  def _swich_hook_high(self):
    self._state.off_hook()

  def _switch_hook_low(self):
    self._state.on_hook()

  def _encoder_pulsed(self):
    if self._state.can('hand_crank_pulsed'):
      self._state.hand_crank_pulsed()
    else:
      self.log().debug('Ignore crank pulse')

  def _rest_switch_pressed(self):
    self._state.hard_reset()

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    pass