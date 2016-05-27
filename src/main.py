import os
import gobject
import handset.base.log
import handset.base.ipc
import handset.bluetooth.profiles
import handset.bluetooth.control
import handset.bluetooth.adapters
import argparse

def main_loop():
  return gobject.MainLoop()

if __name__ == '__main__':
  handset.base.log.send_to_stdout()

  parser = argparse.ArgumentParser(description = 'Bluetooth Handsfree')
  parser.add_argument('--interface', dest = 'interface')
  parser.add_argument('--name', dest = 'name')
  parser.add_argument('--pin', dest = 'pincode')

  args = parser.parse_args()

  #
  # To enforce use of pincode, set `hciconfig <hci> sspmode 0`
  # Using sspmode 1 (Simple Pairing) will cause this application
  # to automatically accept all pairing requests.
  #
  
  session_bus_path = os.environ.get('DBUS_SESSION_BUS_ADDRESS')
  bus = handset.base.ipc.Bus(session_bus_path)

  with handset.bluetooth.adapters.Bluez4(bus, args.interface) as adapter, \
       handset.bluetooth.profiles.HandsFree(bus) as profile, \
       handset.bluetooth.control.Controller(adapter, profile) as control:

    control.start(args.name, args.pincode)
    control.enable_visibility()

    main_loop().run()
