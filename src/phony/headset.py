import time

from phony.base import execute
from phony.base.log import ClassLogger, ScopedLogger, Levels

class HandsFreeHeadset(ClassLogger):
  """
  Behaves like a bluetooth headset, allowing only one device
  to connect/pair at a time, requiring that the device
  provide HFP and voice-dialing capabilities.  The given audio
  device is managed according to whether or not the 'headset'
  is in or initiating a call.  At all other times the audio
  will be muted.
  """

  _started = False
  _bus = None

  _adapter = None
  _hfp = None
  _audio = None

  _device = None
  _hfp_audio_gateway = None

  _on_incoming_call_listeners = []
  _on_call_began_listeners = []
  _on_call_ended_listeners = []
  _on_device_connected_listeners = []

  def __init__(self, bus_provider, adapter, hfp, audio):
    ClassLogger.__init__(self)

    self._bus = bus_provider.session_bus()

    self._adapter = adapter
    self._hfp = hfp
    self._audio = audio

    adapter.on_device_connected(self._device_connected)
    adapter.on_device_disconnected(self._device_disconnected)

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    self.stop()

  @ClassLogger.TraceAs.call(log_level = Levels.INFO, with_arguments = False)
  def start(self, name, pincode):
    if self._started:
      return

    self.enable()

    self._audio.start()
    self.mute_microphone()
    self.mute_speaker()

    self._hfp.start()
    self._adapter.start(name, pincode)

    self._started = True

  @ClassLogger.TraceAs.call(log_level = Levels.INFO)
  def stop(self):
    if self._started:
      self._adapter.stop()
      self._hfp.stop()
      self.reset()

      self._started = False

  @ClassLogger.TraceAs.call(log_level = Levels.INFO)
  def enable(self):
    try:
      self._exec("rfkill unblock bluetooth")
    except Exception, ex:
      self.log().debug('Unable to unblock bluetooth with rfkill: %s' % ex)

  @ClassLogger.TraceAs.call(log_level = Levels.INFO)
  def disable(self):
    try:
      self._exec("rfkill block bluetooth")
    except:
      pass

  def on_incoming_call(self, listener):
    self._on_incoming_call_listeners.append(listener)

  def on_call_began(self, listener):
    self._on_call_began_listeners.append(listener)

  def on_call_ended(self, listener):
    self._on_call_ended_listeners.append(listener)

  def on_device_connected(self, listener):
    self._on_device_connected_listeners.append(listener)

  @ClassLogger.TraceAs.call(log_level = Levels.INFO)
  def enable_pairability(self, timeout = 0):
    self._adapter.enable_pairability(timeout)

  @ClassLogger.TraceAs.call(log_level = Levels.INFO)
  def disable_pairability(self):
    self._adapter.disable_pairability()

  @ClassLogger.TraceAs.call(log_level = Levels.INFO)
  def initiate_call(self):
    if self._hfp_audio_gateway:
      self._call_prologue()
      self._hfp_audio_gateway.begin_voice_dial()
    else:
      self._call_epilogue()
      raise Exception('No audio gateway is connected')

  @ClassLogger.TraceAs.call(log_level = Levels.INFO)
  def cancel_call_initiation(self):
    if self._hfp_audio_gateway:
      self._hfp_audio_gateway.end_voice_dial()
    else:
      raise Exception('No audio gateway is connected')

    self._call_epilogue()

  @ClassLogger.TraceAs.call(log_level = Levels.INFO)
  def dial(self, number):
    if self._hfp_audio_gateway:
      self._call_prologue()
      self._hfp_audio_gateway.dial(number)
    else:
      self._call_epilogue()
      raise Exception('No audio gateway is connected')

  @ClassLogger.TraceAs.call(log_level = Levels.INFO)
  def answer_call(self, path = None):
    if self._hfp_audio_gateway:
      self._call_prologue()
      self._hfp_audio_gateway.answer(path)
    else:
      self._call_epilogue()
      raise Exception('No audio gateway is connected')

  @ClassLogger.TraceAs.call(log_level = Levels.INFO)
  def hangup_call(self, path = None):
    if self._hfp_audio_gateway:
      self._hfp_audio_gateway.hangup(path)
    else:
      raise Exception('No audio gateway is connected')

    self._call_epilogue()

  @ClassLogger.TraceAs.call(log_level = Levels.INFO)
  def deflect_call_to_voicemail(self, path = None):
    if self._hfp_audio_gateway:
      self._hfp_audio_gateway.deflect_to_voicemail(path)
    else:
      raise Exception('No audio gateway is connected')

  @ClassLogger.TraceAs.call(log_level = Levels.INFO)
  def mute_microphone(self):
    self._audio.mute_microphone()

  @ClassLogger.TraceAs.call(log_level = Levels.INFO)
  def unmute_microphone(self):
    self._audio.unmute_microphone()

  @ClassLogger.TraceAs.call(log_level = Levels.INFO)
  def mute_speaker(self):
    self._audio.mute_speaker()

  @ClassLogger.TraceAs.call(log_level = Levels.INFO)
  def unmute_speaker(self):
    self._audio.unmute_speaker()

  @ClassLogger.TraceAs.call(log_level = Levels.INFO)
  def set_microphone_playback_volume(self, volume):
    self._audio.set_microphone_playback_volume(volume)

  @ClassLogger.TraceAs.call(log_level = Levels.INFO)
  def set_microphone_capture_volume(self, volume):
    self._audio.set_microphone_capture_volume(volume)

  @ClassLogger.TraceAs.call(log_level = Levels.INFO)
  def set_volume(self, volume):
    self._audio.set_speaker_volume(volume)

  @ClassLogger.TraceAs.call(log_level = Levels.INFO)
  def reset(self):
    try:
      self.mute_microphone()
      self._adapter.cancel_pending_operations()
      self._hfp.cancel_pending_operations()

      if self._hfp_audio_gateway:
        self._hfp_audio_gateway.dispose()
        self._hfp_audio_gateway = None

      if self._device:
        self._device.dispose()
        self._device = None
    except Exception, ex:
      self.log().warn('Reset error: %s' % ex)

  @ClassLogger.TraceAs.event(log_level = Levels.INFO)
  def get_status(self):
    status = {}

    if self._adapter:
      status['Adapter'] = str(self._adapter)

    if self._device:
      status['Device'] = str(self._device)

    if self._hfp_audio_gateway:
      status['AudioGateway'] = str(self._hfp_audio_gateway)

    if self._audio:
      status['AudioCard'] = str(self._audio)

    return status

  #
  # Bluetooth adapter event callbacks
  #

  @ClassLogger.TraceAs.event(log_level = Levels.INFO)
  def _device_connected(self, device):

    if self._device and device != self._device:
      self.log().info('One device connection allowed.  Disconnecting from previous "%s"' % self._device)
      self.reset()

    self._device = device

    try:
      self._hfp.attach_audio_gateway(
        self._adapter,
        self._device,
        self._audio_gateway_attached
      )
    except Exception, ex:
      self.log().error('Error attaching to HFP gateway: %s' % ex)
      self.reset()

  @ClassLogger.TraceAs.event(log_level = Levels.INFO)
  def _device_disconnected(self, device_path):
    if self._device and device_path == self._device.path():
      self.reset()

  @ClassLogger.TraceAs.event(log_level = Levels.INFO)
  def _audio_gateway_attached(self, audio_gateway):
    if audio_gateway.provides_voice_recognition():
      self._hfp_audio_gateway = audio_gateway
      audio_gateway.on_incoming_call(self._incoming_call)
      audio_gateway.on_call_begin(self._call_began)
      audio_gateway.on_call_end(self._call_ended)

      for listener in self._on_device_connected_listeners:
        listener()
    else:
      self.log().error('Device %s does not provide voice dialing. Disconnecting...')
      self.reset()

  #
  # Audio gateway event handlers:
  #

  @ClassLogger.TraceAs.event(log_level = Levels.INFO)
  def _incoming_call(self, path):
    for listener in self._on_incoming_call_listeners:
      listener(path)

  @ClassLogger.TraceAs.event(log_level = Levels.INFO)
  def _call_began(self, path):
    for listener in self._on_call_began_listeners:
      listener(path)

  @ClassLogger.TraceAs.event(log_level = Levels.INFO)
  def _call_ended(self, path):
    for listener in self._on_call_ended_listeners:
      listener(path)

  #
  # Private methods
  #

  def _call_prologue(self):
    self.unmute_speaker()
    self.unmute_microphone()

  def _call_epilogue(self):
    self.mute_speaker()
    self.mute_microphone()

  def _exec(self, command):
    self.log().debug('Running: ' + command)
    execute.privileged(command, shell = True)