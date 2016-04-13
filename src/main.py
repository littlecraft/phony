import gobject
import handset.base.log
import handset.bluetooth.profiles
import handset.bluetooth.control
import handset.bluetooth.adapters

def main_loop():
  return gobject.MainLoop()

if __name__ == '__main__':
  handset.base.log.send_to_stdout()

  hci_device = 'hci0'
  name = "Ol' Timer"

  with handset.bluetooth.adapters.Bluez4(hci_device) as bluez4, \
       handset.bluetooth.profiles.HandsFree() as profile, \
       handset.bluetooth.control.Controller(bluez4, profile) as control:

    control.start(name)
    control.enable_visibility()

    main_loop().run()
