import os
import gobject
import argparse
import handset.base.log
import handset.base.ipc
import handset.bluetooth.control
import handset.bluetooth.adapters
import handset.bluetooth.profiles.handsfree

from handset.base import log

def main_loop():
  return gobject.MainLoop()

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description = 'Bluetooth Handsfree telephony service')
  parser.add_argument('--interface', help = 'The BT interface to listen on')
  parser.add_argument('--name', help = 'The name to advertise')
  parser.add_argument('--pin', help = 'Pin code to use when Simple Pairing mode is not enabled and/or supported by remote client')
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
  bus = handset.base.ipc.Bus(session_bus_path)

  with handset.bluetooth.adapters.Bluez5(bus, args.interface) as adapter, \
       handset.bluetooth.profiles.handsfree.Ofono(bus) as profile, \
       handset.bluetooth.control.Controller(adapter, profile) as control:

    control.start(args.name, args.pin)
    control.enable_visibility()

    handset.base.log.ScopedLogger
    main_loop().run()
