import dbus
from handset.base.log import ClassLogger

class Bluez5(ClassLogger):
  DBUS_SERVICE_NAME = 'org.bluez'
  DBUS_ADAPTER_INTERFACE = 'org.bluez.Adapter1'
  DBUS_DEVICE_INTERFACE = 'org.bluez.Device1'
  DBUS_PROPERTIES = 'org.freedesktop.DBus.Properties'

  __hci_device = None

  __bus = None

  __adapter = None
  __adapter_properties = None

  __client_endpoint_added_listeners = []
  __client_endpoint_removed_listeners = []

  __started = False

  def __init__(self, bus_constructor, hci_device = None):
    ClassLogger.__init__(self)
    self.__hci_device = hci_device
    self.__bus = bus_constructor.system_bus()

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    pass

  @ClassLogger.TraceAs.call(with_arguments = False)
  def start(self, name, pincode):
    if self.__started:
      return

    self.__adapter = Bluez5Utils.find_adapter(self.__hci_device)
    adapter_path = self.__adapter.object_path
    self.__adapter_properties = Bluez5Utils.properties(adapter_path)

    self.enable()

    if name:
      self.__set_property('Alias', name)

    self.__show_device_properties()

    self.__started = True

  def stop(self):
    if self.visible():
      self.disable_visibility()

  def enable(self):
    self.__set_property('Powered', True)

  def disable(self):
    self.__set_property('Powered', False)

  def enabled(self):
    return self.__get_property('Powered')

  def enable_visibility(self):
    self.__set_property('Discoverable', True)
    self.__set_property('Pairable', True)
    self.__adapter.StartDiscovery()

  def disable_visibility(self):
    self.__set_property('Discoverable', True)
    self.__set_property('Pairable', True)
    self.__adapter.StopDiscovery()

  def visible(self):
    return self.__get_property('Discoverable') and self.__get_property('Pairable')

  def on_client_endpoint_added(self, listener):
    self.__client_endpoint_added_listeners.append(listener)

  def on_client_endpoint_removed(self, listener):
    self.__client_endpoint_removed_listeners.append(listener)

  def __show_device_properties(self):
    self.log().debug('Adapter device id: ' + self.__adapter.object_path)
    self.log().debug('Adapter name: ' + self.__get_property('Name'))
    self.log().debug('Adapter alias: ' + self.__get_property('Alias'))
    self.log().debug('Adapter address: ' + self.__get_property('Address'))
    self.log().debug('Adapter class: 0x%06x' % self.__get_property('Class'))

  def __get_property(self, prop):
    return self.__adapter_properties.Get(self.DBUS_ADAPTER_INTERFACE, prop)

  def __set_property(self, prop, value):
    self.__adapter_properties.Set(self.DBUS_ADAPTER_INTERFACE, prop, value)

class Bluez5Utils:
  """bluez5-x.y/test/bluezutils.py"""

  SERVICE_NAME = "org.bluez"
  ADAPTER_INTERFACE = SERVICE_NAME + ".Adapter1"
  DEVICE_INTERFACE = SERVICE_NAME + ".Device1"

  @staticmethod
  def get_managed_objects():
    bus = dbus.SystemBus()
    manager = dbus.Interface(bus.get_object("org.bluez", "/"),
          "org.freedesktop.DBus.ObjectManager")
    return manager.GetManagedObjects()

  @staticmethod
  def find_adapter(pattern=None):
    return Bluez5Utils.find_adapter_in_objects(
      Bluez5Utils.get_managed_objects(), pattern
    )

  @staticmethod
  def find_adapter_in_objects(objects, pattern=None):
    bus = dbus.SystemBus()
    for path, ifaces in objects.iteritems():
      adapter = ifaces.get(Bluez5Utils.ADAPTER_INTERFACE)
      if adapter is None:
        continue
      if not pattern or pattern == adapter["Address"] or \
                path.endswith(pattern):
        obj = bus.get_object(Bluez5Utils.SERVICE_NAME, path)
        return dbus.Interface(obj, Bluez5Utils.ADAPTER_INTERFACE)
    raise Exception("Bluetooth adapter not found")

  @staticmethod
  def find_device(device_address, adapter_pattern=None):
    return Bluez5Utils.find_device_in_objects(
      Bluez5Utils.get_managed_objects(),
      device_address,
      adapter_pattern
    )

  @staticmethod
  def find_device_in_objects(objects, device_address, adapter_pattern=None):
    bus = dbus.SystemBus()
    path_prefix = ""
    if adapter_pattern:
      adapter = Bluez5Utils.find_adapter_in_objects(objects, adapter_pattern)
      path_prefix = adapter.object_path
    for path, ifaces in objects.iteritems():
      device = ifaces.get(Bluez5Utils.DEVICE_INTERFACE)
      if device is None:
        continue
      if (device["Address"] == device_address and
              path.startswith(path_prefix)):
        obj = bus.get_object(Bluez5Utils.SERVICE_NAME, path)
        return dbus.Interface(obj, Bluez5Utils.DEVICE_INTERFACE)

    raise Exception("Bluetooth device not found")

  @staticmethod
  def properties(path):
    bus = dbus.SystemBus()
    return dbus.Interface(bus.get_object("org.bluez", path),
      "org.freedesktop.DBus.Properties")