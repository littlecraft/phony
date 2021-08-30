from phony.audio.alsa import Alsa

from . import util
test = util.setup()

def test_Alsa_init():
  with Alsa() as audio:
    pass


def test_Alsa_start():
  with Alsa(card_index = 1) as audio:
    audio.start()