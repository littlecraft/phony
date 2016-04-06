import dbus
from dbus.mainloop.glib import DBusGMainLoop
from handset.base import execute
from handset.base.log import ClassLogger

class Bluez4(ClassLogger):
  DBUS_SERVICE_NAME = "org.bluez"
  DBUS_BUS_OBJECT = "/"
  DBUS_MANAGER_INTERFACE = "org.bluez.Manager"
  DBUS_ADAPTER_INTERFACE = "org.bluez.Adapter"

  __bus = None

  __hci_device = None
  __adapter_path = None
  __adapter = None
  __adapter_signal_handler = None

  __started = False

  def __init__(self, hci_device):
    ClassLogger.__init__(self)
    self.__hci_device = hci_device

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    self.stop()

  def start(self):
    if self.__started:
      return

    main_loop = DBusGMainLoop()
    self.__bus = dbus.SystemBus(mainloop = main_loop)

    manager = dbus.Interface(
      self.__bus.get_object(
        self.DBUS_SERVICE_NAME,
        self.DBUS_BUS_OBJECT
      ),
      dbus_interface = self.DBUS_MANAGER_INTERFACE
    )

    self.__adapter_path = manager.FindAdapter(self.__hci_device)
    self.log().debug("Using adapter: " + self.__adapter_path)

    self.__adapter = dbus.Interface(
      self.__bus.get_object(
        self.DBUS_SERVICE_NAME,
        self.__adapter_path
      ),
      dbus_interface = self.DBUS_ADAPTER_INTERFACE
    )
    self.__adapter_signal_handler = Bluez4AdapterSignalHandler(self.__adapter)

    properties = self.__adapter.GetProperties()
    self.log().debug("Adapter name: " + properties["Name"])

    self.__started = True

  def stop(self):
    pass

  def device(self):
    return self.__hci_device

  def start_discovery(self):
    self.__adapter.StartDiscovery()

  def stop_discovery(self):
    self.__adapter.StopDiscovery()

  def enable_visibility(self):
    #self.__exec("piscan")
    pass

  def disable_visibility(self):
    #self.__exec("noscan")
    pass

  def __exec(self, fmt, *args):
    command = "hciconfig " + self.__hci_device + " " + fmt % args
    self.log().debug("Running: " + command)
    execute.privileged(command, shell = True)

class Bluez4AdapterSignalHandler(ClassLogger):
  __adapter = None

  def __init__(self, adapter):
    ClassLogger.__init__(self)
    self.__adapter = adapter
    self.__adapter.connect_to_signal("PropertyChanged", self.property_changed)
    self.__adapter.connect_to_signal("DeviceFound", self.device_found)
    self.__adapter.connect_to_signal("DeviceDisappeared", self.device_disappeared)
    self.__adapter.connect_to_signal("DeviceCreated", self.device_created)
    self.__adapter.connect_to_signal("DeviceRemoved", self.device_removed)

  @ClassLogger.TraceAs.event
  def property_changed(self, name, value):
    self.log().debug('PropertyChange: %s = "%s"' % (name, value))

  @ClassLogger.TraceAs.event
  def device_found(self, address, properties):
    self.log().debug("DeviceFound: " + str(address))

  @ClassLogger.TraceAs.event
  def device_disappeared(self, address):
    pass

  @ClassLogger.TraceAs.event
  def device_created(self, device):
    pass

  @ClassLogger.TraceAs.event
  def device_removed(self, device):
    pass