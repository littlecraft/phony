import cmd
import sys
import dbus
import os

class PhonyShell(cmd.Cmd):
  SOCKET_FILE = '/run/phony/phony.socket'

  PHONY_OBJECT_PATH = '/org/littlecraft/Phony'
  PHONY_SERVICE_NAME = 'org.littlecraft.Phony'

  intro = 'Welcome to phony shell.  Type help or ? for list of commands.\n'
  prompt = '(phony) '
  bus = None
  phony = None

  _session_bus_path = None

  def __init__(self):
    cmd.Cmd.__init__(self)

    self.find_socket_file()

    bus_path = self.session_bus_path()

    if bus_path:
      self.bus = dbus.SessionBus(bus_path)
    else:
      self.bus = dbus.SessionBus()

    try:
      self.phony = self.bus.get_object(self.PHONY_SERVICE_NAME, self.PHONY_OBJECT_PATH)
    except Exception, ex:
      raise Exception('Could not get %s: %s' % (self.PHONY_SERVICE_NAME, ex))

  def find_socket_file(self):
    socket_file = open(self.SOCKET_FILE, 'r')
    self._session_bus_path = socket_file.read()

  def session_bus_path(self):
    if self._session_bus_path:
      os.environ['DBUS_SESSION_BUS_ADDRESS'] = self._session_bus_path
      return self._session_bus_path
    else:
      return os.environ.get('DBUS_SESSION_BUS_ADDRESS')

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

  def do_answer(self, arg):
    try:
      self.phony.Answer()
    except Exception, ex:
      print str(ex)

  def do_hangup(self, arg):
    try:
      self.phony.HangUp()
    except Exception, ex:
      print str(ex)

  def do_mute(self, arg):
    try:
      self.phony.Mute()
    except Exception, ex:
      print str(ex)

  def do_unmute(self, arg):
    try:
      self.phony.Unmute()
    except Exception, ex:
      print str(ex)

  def do_mic_volume(self, arg):
    try:
      self.phony.SetMicrophoneVolume(int(arg))
    except Exception, ex:
      print str(ex)

  def do_speaker_volume(self, arg):
    try:
      self.phony.SetSpeakerVolume(int(arg))
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
      for key,val in status.iteritems():
        print '%s:\t\t%s' % (key, val)
    except Exception, ex:
      print str(ex)

  def do_start_ringing(self, arg):
    try:
      self.phony.StartRinging()
    except Exception, ex:
      print str(ex)

  def do_stop_ringing(self, arg):
    try:
      self.phony.StopRinging()
    except Exception, ex:
      print str(ex)

  def do_short_ring(self, arg):
    try:
      self.phony.ShortRing()
    except Exception, ex:
      print str(ex)

  def do_exit(self, arg):
    sys.exit()

  def do_quit(self, arg):
    sys.exit()

if __name__ == '__main__':
  PhonyShell().cmdloop()