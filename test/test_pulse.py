import unit
import phony.base.ipc
from phony.audio.pulse import PulseAudio

test = unit.setup()

"""
def test_PulseAudio__find_microphone_source():
  audio = PulseAudio()

  assert audio._find_microphone_source()

  source = audio._find_microphone_source('alsa_input.usb-C-Media_Electronics_Inc._USB_Audio_Device-00.analog-mono')
  assert source.name == 'alsa_input.usb-C-Media_Electronics_Inc._USB_Audio_Device-00.analog-mono'
"""

def test_PulseAudio__server_connection():
  with PulseAudio(test.bus_provider) as audio:
    assert audio._get_server_address()
    audio._connect_to_server()

def test_PulseAudio__start():
  with PulseAudio(test.bus_provider) as audio:
    audio.start()

def test_PulseAudio__is_suitable_microphone_source():
  assert PulseAudio._is_suitable_microphone_source('alsa_input.blahblahblah.analog-stereo')
  assert PulseAudio._is_suitable_microphone_source('alsa_input.blahblahblah.analog-mono')
  assert not PulseAudio._is_suitable_microphone_source('alsa_output.blahblahblah.analog-stereo')
  assert not PulseAudio._is_suitable_microphone_source('alsa_output.blahblahblah.analog-stereo.monitor')

def test_PulseAudio__is_suitable_primary_audio_sink():
  assert PulseAudio._is_suitable_primary_audio_sink('alsa_output.blahblahblah.analog-stereo')
  assert PulseAudio._is_suitable_primary_audio_sink('alsa_output.blahblahblah.analog-mono')
  assert not PulseAudio._is_suitable_primary_audio_sink('alsa_input.blahblahblah.analog-stereo')
  assert not PulseAudio._is_suitable_primary_audio_sink('alsa_output.blahblahblah.hdmi-stereo')

def test_PulseAudio__find_microphone_source():
  with PulseAudio(test.bus_provider) as audio:
    audio.start()

    assert audio._find_microphone_source()

    path, properties = audio._find_microphone_source('usb-C-Media_Electronics_Inc')
    assert 'usb-C-Media_Electronics_Inc' in audio._get_device_property(properties, 'Name')

def test_PulseAudio__find_primary_audio_sink():
  with PulseAudio(test.bus_provider) as audio:
    audio.start()

    assert audio._find_primary_audio_sink()

    path, properties = audio._find_primary_audio_sink('usb-C-Media_Electronics_Inc')
    assert 'usb-C-Media_Electronics_Inc' in audio._get_device_property(properties, 'Name')