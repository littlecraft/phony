from fysom import Fysom
from phony.base.log import ClassLogger

class HandCrankTelephoneControls(ClassLogger):
  """
    Old time hand crank telephone HMI:
      Making a call:
        1) Lift the receiver
        2) Turn the hand crank a few times
        3) Speak the name of the person you want to call
           (i.e. "Call the horse doctor")
        4) Have a conversation
      Receiving a call:
        1) When a call comes in, the bells start ringing
        2) Lift the receiver
        3) Say hi, and have a conversation

  Notes:
    Inspiration for the call initiating sequence is taken
    from episodes of Lassie.

    Alex Graham Bell suggested the salutation "ahoy-hoy"
    when answering an incoming call.
  """

  MAGNETO_PULSES_TO_INTITATE_CALL = 8

  _inputs = None
  _ringer = None
  _headset = None

  _state = None

  _magneto_pulse_count = 0

  def __init__(self, io_inputs, bell_ringer, headset):
    ClassLogger.__init__(self)

    self._state = Fysom({
      'initial': 'idle',
      'events': [

        #
        # Defines an event that makes a state transition:
        #
        # {'name': 'event_name', 'src': 'source_state_name', 'dst': 'destination_state_name'}
        #

        #
        # Ingress calling state transitions
        #
        {'name': 'incoming_call', 'src': 'idle',            'dst': 'ringing'},
        {'name': 'call_ended',    'src': 'ringing',         'dst': 'idle'},
        {'name': 'off_hook',      'src': 'ringing',         'dst': 'in_call'},
        # This might happen if the call was answered on the cell phone
        {'name': 'call_began',    'src': 'ringing',         'dst': 'in_call'},

        #
        # Egress calling state transitions
        #
        {'name': 'off_hook',          'src': 'idle',                    'dst': 'waiting_for_hand_crank'},
        {'name': 'hand_crank_turned', 'src': 'waiting_for_hand_crank',  'dst': '='},
        {'name': 'initiate_call',     'src': 'waiting_for_hand_crank',  'dst': 'initiating_call'},
        {'name': 'call_began',        'src': 'initiating_call',         'dst': 'in_call'},

        #
        # In-call state transitions
        #
        {'name': 'on_hook',       'src': '*',               'dst': 'idle'},

        #
        # Ignore these transitions:
        #

        # We don't care about call's ending in any other state except while ringing
        {'name': 'call_ended',      'src': '*',               'dst': '='},
        # Incoming calls in any state other than idle, do not cause a transition
        {'name': 'incoming_call',   'src': '*',               'dst': '='},
        # Ignore off-hook switch bouncing
        {'name': 'off_hook',        'src': '*',               'dst': '='},
        # Ignore magneto pulses unless waiting to initiate a call
        {'name': 'hand_crank_turned',  'src': '*',               'dst': '='},
      ],
      'callbacks': {
        'onchangestate': self._on_change_state,

        # State transition callbacks
        'onidle': self._on_idle,
        'onringing': self._on_ringing,
        'onin_call': self._on_in_call,
        'onhand_crank_turned': self._on_hand_crank_turned,
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
    self._inputs.on_pulse('magneto_sense', self._magneto_pulsed)

  #
  # State change callbacks
  #

  def _on_change_state(self, e):
    self.log().debug('** State: %s -> <%s> -> %s' % (e.src, e.event, e.dst))

  def _on_idle(self, e):
    try:
      self._magneto_pulse_count = 0

      if self._headset:
        if e.src == 'ringing':
          self._ringer.stop_ringing()
        elif e.src == 'in_call':
          self._headset.hangup_call()
        elif e.src == 'initiating_call':
          self._headset.cancel_call_initiation()
          self._headset.hangup_call()

    except Exception, ex:
      self.log().error('Error caught while going idle: %s' % ex)

  def _on_hand_crank_turned(self, e):
    if e.src == 'waiting_for_hand_crank':
      self._magneto_pulse_count = self._magneto_pulse_count + 1

      if self._magneto_pulse_count >= self.MAGNETO_PULSES_TO_INTITATE_CALL:
        self._state.initiate_call()

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
      self._headset.initiate_call()
    except Exception, ex:
      self.log().error('Error caught while going initiating_call: %s' % ex)

  def _on_incoming_call(self, e):
    try:
      if e.src != 'idle':
        self.log().info('Already in call (%s), deflecting new call to voicemail' % e.src)
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
  # Debugging
  #
  def get_state(self):
    return self._state.current

  @ClassLogger.TraceAs.event()
  def simulate_off_hook(self):
    self._state.off_hook()

  @ClassLogger.TraceAs.event()
  def simulate_on_hook(self):
    self._state.on_hook()

  @ClassLogger.TraceAs.event()
  def simulate_hand_crank_turned(self):
    self._state.hand_crank_turned()

  #
  # Low-level IO callbacks
  #

  @ClassLogger.TraceAs.event()
  def _swich_hook_high(self):
    self._state.off_hook()

  @ClassLogger.TraceAs.event()
  def _switch_hook_low(self):
    self._state.on_hook()

  def _magneto_pulsed(self):
    self._state.hand_crank_turned()

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    pass
