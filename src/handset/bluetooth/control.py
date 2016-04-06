from handset.base import execute
from handset.base.log import ClassLogger

class Controller(ClassLogger):
  __adapter = None
  __started = False

  def __init__(self, adapter):
    ClassLogger.__init__(self)
    self.__adapter = adapter

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    self.stop()

  def start(self):
    if self.__started:
      return

    self.enable()
    self.__adapter.start()

  def stop(self):
    if self.__started:
      self.__adapter.stop()

  def enable(self):
    self.log().info("Enabling bluetooth radio")
    self.__exec("rfkill unblock bluetooth")

  def disable(self):
    self.log().info("Disabling bluetooth radio")
    self.__exec("rfkill block bluetooth")

  def enable_visibility(self):
    self.__adapter.start_discovery()

  def disable_visibility(self):
    self.__adapter.stop_discovery()

  def __exec(self, command):
    self.log().debug('Running: ' + command)
    execute.privileged(command, shell = True)