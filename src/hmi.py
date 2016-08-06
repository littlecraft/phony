
from phony.base.log import ClassLogger

class TelephoneControls(ClassLogger):
  _inputs = None

  _on_initiate_call_listeners = []
  _on_answer_listeners = []
  _on_hangup_listeners = []

  _encoder_pulse_count = 0

  def __init__(self, io_inputs):
    ClassLogger.__init__(self)

    self._inputs = io_inputs
    self._inputs.on_rising_edge('hook_switch', self._off_hook)
    self._inputs.on_falling_edge('hook_switch', self._on_hook)
    self._inputs.on_pulse('crank_encoder', self._crank_pulsed)

  def on_initiate_call(self, listener):
    self._on_initiate_call_listeners.append(listener)

  def on_answer(self, listener):
    self._on_answer_listeners.append(listener)

  def on_hangup(self, listener):
    self._on_hangup_listeners.append(listener)

  @ClassLogger.TraceAs.event()
  def _off_hook(self):
    for listener in self._on_answer_listeners:
      listener()
    for listener in self._on_initiate_call_listeners:
      listener()

  @ClassLogger.TraceAs.event()
  def _on_hook(self):
    for listener in self._on_hangup_listeners:
      listener()

  def _crank_pulsed(self):
    self._encoder_pulse_count += 1

    # Provide event source label to speed up tracing
    self.log().event(
      'Pulse count = %d' % self._encoder_pulse_count,
      'TelephoneControls._crank_pulsed()'
    )

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    pass