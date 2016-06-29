import dbus
import dbus.service
from handset.base.log import ClassLogger

class Bluez5(ClassLogger):

  __bus_constructor = None
  __bus = None

  __hci_device = None

  __client_endpoint_added_listeners = []
  __client_endpoint_removed_listeners = []

  def __init__(self, bus_constructor, hci_device):
    ClassLogger.__init__(self)
    self.__hci_device = hci_device
    self.__bus_constructor = bus_constructor

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    pass

  @ClassLogger.TraceAs.call(with_arguments = False)
  def start(self, name, pincode):
    pass

  def stop(self):
    pass

  def enable_visibility(self):
    pass

  def disable_visibility(self):
    pass

  def on_client_endpoint_added(self, listener):
    self.__client_endpoint_added_listeners.append(listener)

  def on_client_endpoint_removed(self, listener):
    self.__client_endpoint_removed_listeners.append(listener)