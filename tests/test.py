import logging
import gobject
import base.classlogger

def setup():
  base.classlogger.send_to_stdout(logging.DEBUG)

def main_loop():
  return gobject.MainLoop()