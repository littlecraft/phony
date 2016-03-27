import logging
import gobject
import base.classlogger
from handset.hfp import Hfp

def main_loop():
  return gobject.MainLoop()

if __name__ == '__main__':
  base.classlogger.send_to_stdout()

  with Hfp() as hfp:
    hfp.start()
    hfp.scan()
    main_loop().run()