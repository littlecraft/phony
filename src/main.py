import gobject
import handset.base.log
import handset.bluetooth.profiles
import handset.bluetooth.control
import handset.bluetooth.adapters

def main_loop():
  return gobject.MainLoop()

if __name__ == '__main__':
  handset.base.log.send_to_stdout()

  #
  # To enforce use of pincode, set `hciconfig <hci> sspmode 0`
  # Using sspmode 1 (Simple Pairing) will cause this application
  # to automatically accept all pairing requests.
  #

  hci_device = '00:1A:7D:DA:71:11'
  name = "Ol' Timer"
  pincode = 1234

  with handset.bluetooth.adapters.Bluez4(hci_device) as adapter, \
       handset.bluetooth.profiles.HandsFree() as profile, \
       handset.bluetooth.control.Controller(adapter, profile) as control:

    control.start(name, pincode)
    control.enable_visibility()

    main_loop().run()
