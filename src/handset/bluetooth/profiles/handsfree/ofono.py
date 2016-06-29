import handset.base.log
from handset.base.log import ClassLogger, Levels

class Ofono(ClassLogger):
  __bus = None

  __audio_gateway_attached_listeners = []
  __audio_gateway_detached_listeners = []

  def __init__(self, bus):
    ClassLogger.__init__(self)

    self.__bus = bus.session_bus()

  @ClassLogger.TraceAs.call()
  def start(self):
    pass

  @ClassLogger.TraceAs.call()
  def stop(self):
    pass

  @ClassLogger.TraceAs.event(log_level = Levels.INFO)
  def attach(self, device_address):
    pass

  def on_attached(self, listener):
    self.__audio_gateway_attached_listeners.append(listener)

  def on_detached(self, listener):
    self.__audio_gateway_detached_listeners.append(listener)

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    pass