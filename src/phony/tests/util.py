import os
import gobject
import phony.base.ipc

from phony.base import log
from phony.base.log import ClassLogger

class Test(ClassLogger):

  bus_provider = None

  def __init__(self):
    ClassLogger.__init__(self)


def setup():
  log.send_to_stdout(log.Levels.DEBUG)

  session_bus_path = os.environ.get('DBUS_SESSION_BUS_ADDRESS')
  if session_bus_path:
    log.static('test').debug('DBUS_SESSION_BUS_ADDRESS=' + session_bus_path)

  test = Test()
  test.bus_provider = phony.base.ipc.BusProvider(session_bus_path)

  return test

