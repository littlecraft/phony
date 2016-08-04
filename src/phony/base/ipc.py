import dbus

from dbus.mainloop.glib import DBusGMainLoop

class BusProvider:
  _bus_address = None

  def __init__(self, session_bus_address = None):
    self._bus_address = session_bus_address

  def system_bus(self):
    return dbus.SystemBus(mainloop = self._main_loop())

  def session_bus(self):
    main_loop = self._main_loop()
    if self._bus_address:
      return dbus.bus.BusConnection(self._bus_address, mainloop = main_loop)
    else:
      return dbus.SessionBus(mainloop = main_loop)

  def _main_loop(self):
    return DBusGMainLoop()