import os
import dbus
import gobject
import argparse
import behavior
import phony.base.ipc
import phony.bluetooth.adapters
import phony.bluetooth.profiles.handsfree

from phony.base import log
from phony.base.log import ClassLogger, ScopedLogger

class ApplicationMain(ClassLogger):
  def __init__(self):
    ClassLogger.__init__(self)

  def main_loop(self):
    return gobject.MainLoop()

  def run(self):
    parser = argparse.ArgumentParser(description = 'Bluetooth Handsfree telephony service')
    parser.add_argument('--interface', help = 'The BT interface to listen on')
    parser.add_argument('--name', help = 'The name to advertise')
    parser.add_argument('--pin', help = 'Pin code to use when Simple Pairing mode is not enabled and/or unsupported by remote client')
    parser.add_argument('--visibility-timeout', default = 0, help = 'Duration (seconds) to remain visible and pairable (default is 0, no timeout)')
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
         behavior.HandsFreeHeadset(bus, adapter, hfp) as headset:

      headset.start(args.name, args.pin)
      headset.enable_pairability(args.visibility_timeout)

      with ScopedLogger(self, 'main_loop'):
        self.main_loop().run()

if __name__ == '__main__':
  main = ApplicationMain()
  main.run()
