import gobject
import base.log

def setup():
  base.log.send_to_stdout(base.log.Levels.DEBUG)

def main_loop():
  return gobject.MainLoop()