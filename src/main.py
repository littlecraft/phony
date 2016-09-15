import os
import sys
import dbus
import signal
import gobject
import argparse

import hmi
import debug
import ringer
import headset

import phony.base.ipc
import phony.io.raspi
import phony.audio.alsa
import phony.bluetooth.adapters
import phony.bluetooth.profiles.handsfree

from phony.base import log
from phony.base.log import ClassLogger, ScopedLogger

class ApplicationMain(ClassLogger):
  LOCK_FILE_NAME = '.phony.lock'

  input_layout = {
    'reset_switch': {
      'pin': 2,
      'debounce': 50,
      'pull_up_down': 'up'
    },
    'hook_switch': {
      'pin': 3,
      'debounce': 200,
      'pull_up_down': 'up'
    },
    'hand_crank_encoder': {
      'pin': 26,
      'debounce': 50,
      'pull_up_down': 'down'
    }
  }

  output_layout = {
    'ringer_enable': {
      'pin': 4,
      'default': 0,
      'invert_logic': True
    },
    'ringer_1': {
      'pin': 12,
      'default': 0
    },
    'ringer_2': {
      'pin': 13,
      'default': 0
    }
  }

  def __init__(self):
    ClassLogger.__init__(self)

  def main_loop(self):
    return gobject.MainLoop()

  def sigint_handler(self, signal, frame):
    self.log().info('SIGINT, exiting...')
    self.remove_lock_file()
    sys.exit(1)

  def session_bus_path(self):
    return os.environ.get('DBUS_SESSION_BUS_ADDRESS')

  def aquire_lock_file(self):
    if os.path.isfile(self.LOCK_FILE_NAME):
      raise Exception('Lock file exists, already running?')

    lock_file = open(self.LOCK_FILE_NAME, 'w')

    session_bus_path = self.session_bus_path()
    if session_bus_path:
      lock_file.write(session_bus_path)

  def remove_lock_file(self):
    if os.path.isfile(self.LOCK_FILE_NAME):
      os.remove(self.LOCK_FILE_NAME)

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

    self.aquire_lock_file()

    level = log.Levels.parse(args.log_level)
    log.send_to_stdout(level = level)

    #
    # To enforce use of pincode, set `hciconfig <hci> sspmode 0`
    # Using sspmode 1 (Simple Pairing) will cause this application
    # to automatically accept all pairing requests.
    #

    session_bus_path = self.session_bus_path()
    if session_bus_path:
      self.log().debug('DBUS_SESSION_BUS_ADDRESS=' + session_bus_path)

    bus = phony.base.ipc.BusProvider(session_bus_path)

    with phony.bluetooth.adapters.Bluez5(bus, args.interface) as adapter, \
         phony.bluetooth.profiles.handsfree.Ofono(bus) as hfp, \
         phony.audio.alsa.Alsa(args.audio_card_index) as audio, \
         headset.HandsFreeHeadset(bus, adapter, hfp, audio) as hs:

      hs.start(args.name, args.pin)
      hs.enable_pairability(args.visibility_timeout)

      with phony.io.raspi.Inputs(self.input_layout) as io_inputs, \
           phony.io.raspi.Outputs(self.output_layout) as io_outputs, \
           ringer.Njm2670HbridgeRinger(io_outputs) as bell_ringer, \
           hmi.HandCrankTelephoneControls(io_inputs, bell_ringer, hs) as controls, \
           debug.DbusDebugInterface(bus, hs, bell_ringer) as debug_interface:

        with ScopedLogger(self, 'main_loop'):
          self.main_loop().run()

    self.remove_lock_file()

if __name__ == '__main__':
  main = ApplicationMain()
  main.run()
