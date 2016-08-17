import os
import sys
import dbus
import signal
import gobject
import argparse

import hmi
import debug
import headset

import phony.base.ipc
import phony.io.raspi
import phony.audio.alsa
import phony.bluetooth.adapters
import phony.bluetooth.profiles.handsfree

from phony.base import log
from phony.base.log import ClassLogger, ScopedLogger

class ApplicationMain(ClassLogger):
  pin_layout = {
    'reset_switch': {
      'pin': 20,
      'direction': 'input',
      'debounce': 200,
      'polarity': 'pull-up'
    },
    'hook_switch': {
      'pin': 21,
      'direction': 'input',
      'debounce': 200,
      'polarity': 'pull-up'
    },
    'hand_crank_encoder': {
      'pin': 26,
      'direction': 'input',
      'debounce': 50,
      'polarity': 'pull-up'
    }
  }

  def __init__(self):
    ClassLogger.__init__(self)

  def main_loop(self):
    return gobject.MainLoop()

  def sigint_handler(self, signal, frame):
    self.log().info('SIGINT, exiting...')
    sys.exit(1)

  def run(self):
    signal.signal(signal.SIGINT, self.sigint_handler)

    parser = argparse.ArgumentParser(description = 'Bluetooth Handsfree telephony service')
    parser.add_argument('--interface', help = 'The BT interface to listen on')
    parser.add_argument('--name', help = 'The name to advertise')
    parser.add_argument('--pin', help = 'Pin code to use when Simple Pairing mode is not enabled and/or unsupported by remote client')
    parser.add_argument('--visibility-timeout', default = 0, type = int, help = 'Duration (seconds) to remain visible and pairable (default is 0, no timeout)')
    parser.add_argument('--audio-card-index', default = -1, type = int, help = 'ALSA audio card index to use for capture and playback')
    parser.add_argument('--log-level', default = 'DEFAULT', help = 'Logging level: DEFAULT, CRITICAL, ERROR, WARNING, INFO, DEBUG')

    args = parser.parse_args()

    level = log.Levels.parse(args.log_level)
    log.send_to_stdout(level = level)

    #
    # To enforce use of pincode, set `hciconfig <hci> sspmode 0`
    # Using sspmode 1 (Simple Pairing) will cause this application
    # to automatically accept all pairing requests.
    #

    session_bus_path = os.environ.get('DBUS_SESSION_BUS_ADDRESS')
    if session_bus_path:
      self.log().debug('DBUS_SESSION_BUS_ADDRESS=' + session_bus_path)

    bus = phony.base.ipc.BusProvider(session_bus_path)

    with phony.bluetooth.adapters.Bluez5(bus, args.interface) as adapter, \
         phony.bluetooth.profiles.handsfree.Ofono(bus) as hfp, \
         phony.audio.alsa.Alsa(args.audio_card_index) as audio, \
         headset.HandsFreeHeadset(bus, adapter, hfp, audio) as hands_free_headset:

      hands_free_headset.start(args.name, args.pin)
      hands_free_headset.enable_pairability(args.visibility_timeout)

      with phony.io.raspi.Inputs(self.pin_layout) as io_inputs, \
           hmi.HandCrankTelephoneControls(io_inputs, hands_free_headset) as controls, \
           debug.DbusDebugInterface(bus, hands_free_headset) as debug_interface:

        with ScopedLogger(self, 'main_loop'):
          self.main_loop().run()

if __name__ == '__main__':
  main = ApplicationMain()
  main.run()
