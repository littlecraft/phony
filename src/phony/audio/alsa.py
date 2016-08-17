import alsaaudio

from phony.base.log import static, ClassLogger

class Alsa(ClassLogger):
  _card_name = None
  _card_index = None
  _microphone_mixer = None

  def __init__(self, card_name = None):
    ClassLogger.__init__(self)

    self._card_name = card_name

  @ClassLogger.TraceAs.call()
  def start(self):
    self._card_index = self._find_card_index(self._card_name)
    self._microphone_mixer = self._find_microphone_mixer(self._card_index)

    self._show_properties()

  def mute_microphone(self):
    if self._can_mute_microphone_playback():
      self._microphone_mixer.setmute(1)
    if self._can_mute_microphone_capture():
      self._microphone_mixer.setrec(0)

  def unmute_microphone(self):
    if self._can_mute_microphone_playback():
      self._microphone_mixer.setmute(0)
    if self._can_mute_microphone_capture():
      self._microphone_mixer.setrec(1)

  def _find_card_index(self, card_name = None):
    if not card_name:
      return -1
    else:
      return alsaaudio.cards().index(card_name)

  def _find_microphone_mixer(self, card_index = -1):
    mixers = alsaaudio.mixers(card_index)

    if not 'Mic' in mixers:
      raise Exception('No microphone mixer found for card %s. Available: %s. %s'
        % (card_index, mixers, ex))

    return alsaaudio.Mixer(control = 'Mic', cardindex = card_index)

  def _can_mute_microphone_playback(self):
    return 'Playback Mute' in self._microphone_mixer.switchcap()

  def _can_mute_microphone_capture(self):
    return 'Capture Mute' in self._microphone_mixer.switchcap()

  def _show_properties(self):
    self.log().debug('Audio card name: %s' % self._microphone_mixer.cardname())
    self.log().debug('Microphone mixer id: %s' % self._microphone_mixer.mixerid())
    self.log().debug('Microphone mixer capabilities: %s' % self._microphone_mixer.switchcap())
    self.log().debug('Microphone mute: %s', self._microphone_mixer.getmute())

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    pass