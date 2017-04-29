import alsaaudio

from phony.base.log import static, ClassLogger

class Alsa(ClassLogger):
  CARD_INDICES_TO_TRY = 5

  _card_index = None
  _microphone_mixer = None
  _speaker_mixer = None

  def __init__(self, card_index = -1):
    ClassLogger.__init__(self)

    self._card_index = card_index
    self._speaker_mixer, self._microphone_mixer = \
      self._find_suitable_mixers(self._card_index)

    if not self._speaker_mixer or not self._microphone_mixer:
      raise Exception('An audio device with a speaker and a microphone mixer is required, but could not be found. card_index = "%s"' % self._card_index)

  @ClassLogger.TraceAs.call()
  def start(self):
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

  @ClassLogger.TraceAs.event()
  def mute_speaker(self):
    if self._can_mute_speaker_playback():
      self._speaker_mixer.setmute(1)

  @ClassLogger.TraceAs.event()
  def unmute_speaker(self):
    if self._can_mute_speaker_playback():
      self._speaker_mixer.setmute(0)

  @ClassLogger.TraceAs.event()
  def set_microphone_playback_volume(self, volume):
    for channel in range(0, self._microphone_channel_count()):
      self._microphone_mixer.setvolume(volume, channel, alsaaudio.PCM_PLAYBACK)

  @ClassLogger.TraceAs.event()
  def set_microphone_capture_volume(self, volume):
    for channel in range(0, self._microphone_channel_count()):
      self._microphone_mixer.setvolume(volume, channel, alsaaudio.PCM_CAPTURE)

  @ClassLogger.TraceAs.event()
  def set_speaker_volume(self, volume):
    self._speaker_mixer.setvolume(volume)

  def _microphone_channel_count(self):
    return len(self._microphone_mixer.getvolume())

  def _find_suitable_mixers(self, card_index = -1):
    mic = None
    speaker = None

    if card_index < 0:
      for card_index in range(0, Alsa.CARD_INDICES_TO_TRY):
        try:
          mixers = alsaaudio.mixers(cardindex = card_index)

          if 'Mic' in mixers and 'Speaker' in mixers:
            mic = alsaaudio.Mixer(control = 'Mic', cardindex = card_index)
            speaker = alsaaudio.Mixer(control = 'Speaker', cardindex = card_index)
            break

        except Exception:
          pass
    else:
      mixers = alsaaudio.mixers(cardindex = card_index)

      if 'Mic' in mixers and 'Speaker' in mixers:
        mic = alsaaudio.Mixer(control = 'Mic', cardindex = card_index)
        speaker = alsaaudio.Mixer(control = 'Speaker', cardindex = card_index)

    return speaker, mic

  def _can_mute_microphone_playback(self):
    return 'Playback Mute' in self._microphone_mixer.switchcap()

  def _can_mute_microphone_capture(self):
    return 'Capture Mute' in self._microphone_mixer.switchcap()

  def _can_mute_speaker_playback(self):
    return 'Playback Mute' in self._speaker_mixer.switchcap()

  def _show_properties(self):
    self.log().debug('Audio card name: %s' % self._microphone_mixer.cardname())
    self.log().debug('Speaker mixer capabilities: %s' % self._speaker_mixer.switchcap())
    self.log().debug('Speaker playback volume: %s' % self._speaker_mixer.getvolume(alsaaudio.PCM_PLAYBACK))
    self.log().debug('Speaker playback mute: %s' % self._speaker_mixer.getmute())
    self.log().debug('Microphone mixer capabilities: %s' % self._microphone_mixer.switchcap())
    self.log().debug('Microphone playback mute: %s' % self._microphone_mixer.getmute())
    self.log().debug('Microphone capture enabled: %s' % self._microphone_mixer.getrec())
    self.log().debug('Microphone playback volume: %s' % self._microphone_mixer.getvolume(alsaaudio.PCM_PLAYBACK))
    self.log().debug('Microphone capture volume: %s' % self._microphone_mixer.getvolume(alsaaudio.PCM_CAPTURE))

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    pass

  def __repr__(self):
    if self._speaker_mixer:
      return self._speaker_mixer.cardname()
    else:
      return 'n/a'