import dbus
import os

from dbus.mainloop.glib import DBusGMainLoop

class BusProvider:
  path = None

  def __init__(self, session_bus_path=None):
    self.path = session_bus_path

  def system_bus(self):
    return dbus.SystemBus(mainloop = self._main_loop())

  def session_bus(self):
    main_loop = self._main_loop()
    if self.path:
      return dbus.bus.BusConnection(self.path, mainloop=main_loop)
    else:
      return dbus.SessionBus(mainloop = main_loop)

  def __repr__(self):
    if self.path:
      return self.path
    else:
      return ''

  def _main_loop(self):
    return DBusGMainLoop()

class OwnedSocketFile:
  def __init__(self, bus, socket_file):
    self.socket_file = socket_file
    self.create_socket_file(bus)

  def create_socket_file(self, bus):
    if os.path.isfile(self.socket_file):
      raise Exception('Socket file %s exists, already running?' % self.socket_file)

    try:
      socket_file = open(self.socket_file, 'w')

      if bus.path:
        socket_file.write(str(bus))
    except Exception, ex:
      self.log().warning('Unable to write socket file %s: %s' % (self.socket_file, ex))

  def remove_socket_file(self):
    try:
      if os.path.isfile(self.socket_file):
        os.remove(self.socket_file)
    except Exception, ex:
      self.log().warning('Unable to remove socket file %s: %s' % (self.socket_file, ex))

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    self.remove_socket_file()


