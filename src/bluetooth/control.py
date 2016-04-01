import subprocess
from base.log import ClassLogger

class Controller(ClassLogger):
  __adapter = None

  def __init__(self, adapter):
    ClassLogger.__init__(self)
    self.__adapter = adapter
    self.enable()

  def enable(self):
    self.log().info("Enabling bluetooth radio")
    subprocess.check_output("rfkill unblock bluetooth", shell = True)

  def disable(self):
    self.log().info("Disabling bluetooth radio")
    subprocess.check_output("rfkill block bluetooth", shell = True)

  def enable_visibility(self):
    self.__adapter.enable_visibility()

  def disable_visibility(self):
    self.__adapter.disable_visibility()