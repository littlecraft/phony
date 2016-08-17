import unit

from phony.audio.alsa import Alsa

test = unit.setup()

def test_Alsa_init():
  with Alsa() as audio:
    pass

def test_Alsa_start():
  with Alsa(card_index = 1) as audio:
    audio.start()