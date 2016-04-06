import gobject
import handset.base.log
import handset.bluetooth.profiles
import handset.bluetooth.control
import handset.bluetooth.adapters

def main_loop():
  return gobject.MainLoop()

if __name__ == '__main__':
  handset.base.log.send_to_stdout()

  hci_device = 'hci1'

  with handset.bluetooth.adapters.Bluez4(hci_device) as bluez4, \
       handset.bluetooth.control.Controller(bluez4) as control, \
       handset.bluetooth.profiles.HandsFree() as hfp:

    control.start()
    hfp.start()

    control.enable_visibility()

    main_loop().run()
