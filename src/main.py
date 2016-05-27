import handset.bluetooth.profiles
import handset.bluetooth.control
import handset.bluetooth.adapters
import gobject
import argparse

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

  log.send_to_stdout(log.Levels.parse(args.log_level))

  #
  # To enforce use of pincode, set `hciconfig <hci> sspmode 0`
  # Using sspmode 1 (Simple Pairing) will cause this application
  # to automatically accept all pairing requests.
  #

  with handset.bluetooth.adapters.Bluez4(args.interface) as adapter, \
       handset.bluetooth.profiles.HandsFree() as profile, \
       handset.bluetooth.control.Controller(adapter, profile) as control:

    control.start(args.name, args.pin)
    control.enable_visibility()

    main_loop().run()
