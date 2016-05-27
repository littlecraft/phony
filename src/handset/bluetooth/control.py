from handset.base import execute
from handset.base.log import ClassLogger
from handset.base.log import Levels

class Controller(ClassLogger):
  __adapter = None
  __profile = None
  __started = False

  def __init__(self, adapter, profile):
    ClassLogger.__init__(self)
    self.__adapter = adapter
    self.__profile = profile

    adapter.on_client_endpoint_added(self.client_endpoint_added)
    adapter.on_client_endpoint_removed(self.client_endpoint_removed)

    profile.on_attached(self.profile_attached)
    profile.on_detached(self.profile_detached)

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    self.stop()

  @ClassLogger.TraceAs.call(with_arguments = False)
  def start(self, name, pincode):
    if self.__started:
      return

    self.enable()
    self.__profile.start()
    self.__adapter.start(name, pincode)

  def stop(self):
    if self.__started:
      self.__adapter.stop()
      self.__profile.stop()

  def enable(self):
    self.log().info("Enabling radio")
    # TODO: Ignore if rfkill is not available
    self.__exec("rfkill unblock bluetooth")

  def disable(self):
    self.log().info("Disabling radio")
    self.__exec("rfkill block bluetooth")

  def enable_visibility(self):
    self.__adapter.enable_visibility()

  def disable_visibility(self):
    self.__adapter.enable_visibility()

  @ClassLogger.TraceAs.event(log_level = Levels.INFO)
  def client_endpoint_added(self, address):
    self.__profile.attach(address)

  @ClassLogger.TraceAs.event(log_level = Levels.INFO)
  def client_endpoint_removed(self, address):
    pass

  @ClassLogger.TraceAs.event(log_level = Levels.INFO)
  def profile_attached(self):
    pass

  @ClassLogger.TraceAs.event(log_level = Levels.INFO)
  def profile_detached(self):
    pass

  def __exec(self, command):
    self.log().debug('Running: ' + command)
    execute.privileged(command, shell = True)