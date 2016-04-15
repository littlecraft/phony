from handset.base import execute
from handset.base.log import ClassLogger

class Controller(ClassLogger):
  __adapter = None
  __profile = None
  __started = False

  def __init__(self, adapter, profile):
    ClassLogger.__init__(self)
    self.__adapter = adapter
    self.__profile = profile

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    self.stop()

  @ClassLogger.TraceAs.call(with_arguments = False)
  def start(self, name, pincode):
    if self.__started:
      return

    self.enable()
    self.__adapter.start(name, pincode)
    #self.__profile.start()

  def stop(self):
    if self.__started:
      self.__adapter.stop()
      self.__profile.stop()

  def enable(self):
    self.log().info("Enabling radio")
    self.__exec("rfkill unblock bluetooth")

  def disable(self):
    self.log().info("Disabling radio")
    self.__exec("rfkill block bluetooth")

  def enable_visibility(self):
    self.__adapter.enable_visibility()

  def disable_visibility(self):
    self.__adapter.enable_visibility()

  def __exec(self, command):
    self.log().debug('Running: ' + command)
    execute.privileged(command, shell = True)