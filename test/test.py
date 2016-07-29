import gobject
import handset.base.log

def setup():
  handset.base.log.send_to_stdout(base.log.Levels.DEBUG)

def main_loop():
  return gobject.MainLoop()
