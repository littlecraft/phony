import cmd
import sys
import dbus

PHONY_OBJECT_PATH = '/org/littlecraft/Phony'
PHONY_SERVICE_NAME = 'org.littlecraft.Phony'

class PhonyShell(cmd.Cmd):
  intro = 'Welcome to phony shell.  Type help or ? for list of commands.\n'
  prompt = '(phony) '
  bus = None
  phony = None

  def __init__(self):
    cmd.Cmd.__init__(self)

    self.bus = dbus.SessionBus()

    self.phony = self.bus.get_object(PHONY_SERVICE_NAME, PHONY_OBJECT_PATH)
    if not self.phony:
      raise Exception('Could not get %s' % PHONY_SERVICE_NAME)

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

if __name__ == '__main__':
  PhonyShell().cmdloop()