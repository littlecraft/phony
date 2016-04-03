import base.execute
from base.log import ClassLogger

class Controller(ClassLogger):
  __adapter = None

  def __init__(self, adapter):
    ClassLogger.__init__(self)
    self.__adapter = adapter
    self.enable()

  def enable(self):
    self.log().info("Enabling bluetooth radio")
    self.__exec("rfkill unblock bluetooth")

  def disable(self):
    self.log().info("Disabling bluetooth radio")
    self.__exec("rfkill block bluetooth")

  def enable_visibility(self):
    self.__adapter.enable_visibility()

  def disable_visibility(self):
    self.__adapter.disable_visibility()

  def __exec(self, command):
    self.log().debug('Running: ' + command)
    base.execute.privileged(command, shell = True)