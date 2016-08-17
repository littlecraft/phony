import alsaaudio

from phony.base.log import static, ClassLogger

class Alsa(ClassLogger):
  CARD_INDICES_TO_TRY = 5

  _card_index = None
  _microphone_mixer = None

  def __init__(self, card_index = -1):
    ClassLogger.__init__(self)

    self._card_index = card_index

  @ClassLogger.TraceAs.call()
  def start(self):
    self._microphone_mixer = self._find_suitable_mixer(self._card_index)
    if not self._microphone_mixer:
      raise Exception('No microphone mixer found. card_index = "%s"' % self._card_index)

    self._show_properties()

  @ClassLogger.TraceAs.event()
  def mute_microphone(self):
    if self._can_mute_microphone_playback():
      self._microphone_mixer.setmute(1)
    if self._can_mute_microphone_capture():
      self._microphone_mixer.setrec(0)

  @ClassLogger.TraceAs.event()
  def unmute_microphone(self):
    if self._can_mute_microphone_playback():
      self._microphone_mixer.setmute(0)
    if self._can_mute_microphone_capture():
      self._microphone_mixer.setrec(1)

  def _find_suitable_mixer(self, card_index = -1):
    mic_mixer = None

    if card_index < 0:
      for card_index in range(0, Alsa.CARD_INDICES_TO_TRY):
        try:
          mixers = alsaaudio.mixers(cardindex = card_index)
          if 'Mic' in mixers:
            mic_mixer = alsaaudio.Mixer(control = 'Mic', cardindex = card_index)
            break
        except Exception:
          pass
    else:
      mixers = alsaaudio.mixers(cardindex = card_index)
      if 'Mic' in mixers:
        mic_mixer = alsaaudio.Mixer(control = 'Mic', cardindex = card_index)

    return mic_mixer

  def _can_mute_microphone_playback(self):
    return 'Playback Mute' in self._microphone_mixer.switchcap()

  def _can_mute_microphone_capture(self):
    return 'Capture Mute' in self._microphone_mixer.switchcap()

  def _show_properties(self):
    self.log().debug('Audio card name: %s' % self._microphone_mixer.cardname())
    self.log().debug('Microphone mixer capabilities: %s' % self._microphone_mixer.switchcap())
    self.log().debug('Microphone playback mute: %s' % self._microphone_mixer.getmute())
    self.log().debug('Microphone capture mute: %s' % self._microphone_mixer.getrec())

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    pass