import os
import sys
import dbus
import signal
import gobject

import ast
import argparse
import ConfigParser

import hmi
import debug
import ringer

import phony.headset
import phony.base.ipc
import phony.io.raspi
import phony.audio.alsa
import phony.bluetooth.adapters
import phony.bluetooth.profiles.handsfree

from phony.base import log
from phony.base.log import ClassLogger, ScopedLogger

class DictionaryConfig(ConfigParser.ConfigParser):
  def __init__(self):
    ConfigParser.ConfigParser.__init__(self)

  def flatten_and_parse_types(self):
    d = {}
    for k in self._sections:
      d.update(dict(self._defaults, **self._sections[k]))
      d.pop('__name__', None)

    for k, v in d.iteritems():
      try:
        d[k] = ast.literal_eval(v)
      except (SyntaxError, ValueError):
        d[k] = v

    return d

class ApplicationMain(ClassLogger):
  CONFIG_FILE = '/etc/crankphone/crankphone.conf'
  SOCKET_FILE = '/run/crankphone/crankphone.socket'

  input_layout = {
    'reset_switch': {
      'pin': 27,
      'debounce': 200,
      'pull_up_down': 'up'
    },
    'hook_switch': {
      'pin': 17,
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
      'pin': 22,
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
    self.remove_socket_file()
    sys.exit(1)

  def session_bus_path(self):
    return os.environ.get('DBUS_SESSION_BUS_ADDRESS')

  def create_socket_file(self):
    if os.path.isfile(self.SOCKET_FILE):
      raise Exception('Socket file %s exists, already running?' % self.SOCKET_FILE)

    try:
      socket_file = open(self.SOCKET_FILE, 'w')

      session_bus_path = self.session_bus_path()
      if session_bus_path:
        socket_file.write(session_bus_path)
    except Exception, ex:
      self.log().warning('Unable to write socket file %s: %s' % (self.SOCKET_FILE, ex))

  def remove_socket_file(self):
    try:
      if os.path.isfile(self.SOCKET_FILE):
        os.remove(self.SOCKET_FILE)
    except Exception, ex:
      self.log().warning('Unable to remove socket file %s: %s' % (self.SOCKET_FILE, ex))

  def configuration(self, args):
    merged = {
      'log_level': 'DEFAULT',
      'interface': None,
      'name': None,
      'pin': None,
      'visibility_timeout': 0,
      'audio_card_index': -1
    }

    if args.config_file:
      config_file = args.config_file
    else:
      config_file = self.CONFIG_FILE

    if os.path.isfile(config_file):
      config = DictionaryConfig()
      config.read(config_file)

      merged.update(config.flatten_and_parse_types())
    else:
      if config_file != self.CONFIG_FILE:
        raise Exception('Cannot find config file: %s' % config_file)

    args_with_values = dict((k, v) for k, v in vars(args).iteritems() if v != None)
    merged.update(args_with_values)
    return argparse.Namespace(**merged)

  def run(self):
    signal.signal(signal.SIGINT, self.sigint_handler)

    parser = argparse.ArgumentParser(description = 'Bluetooth Handsfree telephony service')
    parser.add_argument('--interface', help = 'The BT interface to listen on')
    parser.add_argument('--name', help = 'The name to advertise')
    parser.add_argument('--pin', help = 'Pin code to use when Simple Pairing mode is not enabled and/or unsupported by remote client')
    parser.add_argument('--visibility-timeout', type = int, help = 'Duration (seconds) to remain visible and pairable (default is 0, no timeout)')
    parser.add_argument('--audio-card-index', type = int, help = 'ALSA audio card index to use for capture and playback')
    parser.add_argument('--log-level', help = 'Logging level: DEFAULT, CRITICAL, ERROR, WARNING, INFO, DEBUG')
    parser.add_argument('--config-file', help = 'Path to configuration file')

    config = self.configuration(parser.parse_args())

    level = log.Levels.parse(config.log_level)
    log.send_to_stdout(level = level)

    self.create_socket_file()

    #
    # To enforce use of pincode, set `hciconfig <hci> sspmode 0`
    # Using sspmode 1 (Simple Pairing) will cause this application
    # to automatically accept all pairing requests.
    #

    session_bus_path = self.session_bus_path()
    bus = phony.base.ipc.BusProvider(session_bus_path)

    with phony.bluetooth.adapters.Bluez5(bus, config.interface) as adapter, \
         phony.bluetooth.profiles.handsfree.Ofono(bus) as hfp, \
         phony.audio.alsa.Alsa(config.audio_card_index) as audio, \
         phony.headset.HandsFreeHeadset(bus, adapter, hfp, audio) as hs:

      hs.start(config.name, config.pin)
      hs.enable_pairability(config.visibility_timeout)

      with phony.io.raspi.Inputs(self.input_layout) as io_inputs, \
           phony.io.raspi.Outputs(self.output_layout) as io_outputs, \
           ringer.BellRinger(io_outputs) as bells, \
           hmi.HandCrankTelephoneControls(io_inputs, bells, hs), \
           debug.DbusDebugInterface(bus, hs, bells):

        with ScopedLogger(self, 'main_loop'):
          self.main_loop().run()

    self.remove_socket_file()

if __name__ == '__main__':
  main = ApplicationMain()
  main.run()
