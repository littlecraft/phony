import cmd
import sys
import dbus
import os

class PhonyShell(cmd.Cmd):
  PHONY_OBJECT_PATH = '/org/littlecraft/Phony'
  PHONY_SERVICE_NAME = 'org.littlecraft.Phony'

  intro = 'Welcome to phony shell.  Type help or ? for list of commands.\n'
  prompt = '(phony) '
  bus = None
  phony = None

  def __init__(self):
    cmd.Cmd.__init__(self)

    session_bus_path = os.environ.get('DBUS_SESSION_BUS_ADDRESS')

    if session_bus_path:
      self.bus = dbus.SessionBus(session_bus_path)
    else:
      self.bus = dbus.SessionBus()

    try:
      self.phony = self.bus.get_object(self.PHONY_SERVICE_NAME, self.PHONY_OBJECT_PATH)
    except Exception, ex:
      raise Exception('Could not get %s: %s' % (self.PHONY_SERVICE_NAME, ex))

  def do_voice(self, arg):
    try:
      self.phony.BeginVoiceDial()
    except Exception, ex:
      print str(ex)

  def do_dial(self, arg):
    try:
      self.phony.Dial(arg)
    except Exception, ex:
      print str(ex)

  def do_hangup(self, arg):
    try:
      self.phony.HangUp()
    except Exception, ex:
      print str(ex)

  def do_reset(self, arg):
    try:
      self.phony.Reset()
    except Exception, ex:
      print str(ex)

  def do_status(self, arg):
    try:
      status = self.phony.GetStatus()
      print status
    except Exception, ex:
      print str(ex)

  def do_exit(self, arg):
    sys.exit()

  def do_quit(self, arg):
    sys.exit()

if __name__ == '__main__':
  PhonyShell().cmdloop()