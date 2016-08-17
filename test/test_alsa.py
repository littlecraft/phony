import unit

from phony.audio.alsa import Alsa

test = unit.setup()

def test_Alsa_init():
  with Alsa() as audio:
    pass

def test_Alsa__find_card_index():
  with Alsa() as audio:
    assert audio._find_card_index('Device') >= 0

def test_Alsa__find_microphone_mixer():
  with Alsa() as audio:
    card_index = audio._find_card_index('Device')
    assert audio._find_microphone_mixer(card_index)

def test_Alsa_start():
  with Alsa('Device') as audio:
    audio.start()