import dbus

from phony.base import execute
from phony.base.log import ClassLogger

class Bluez5(ClassLogger):
  AGENT_PATH = '/phony/agent/bluez'
  __agent = None

  __hci_device = None

  __bus = None

  __adapter = None
  __adapter_properties = None

  __on_device_connected_listeners = []
  __on_device_disconnected_listeners = []

  __started = False

  def __init__(self, bus_constructor, hci_device = None):
    ClassLogger.__init__(self)
    self.__hci_device = hci_device
    self.__bus = bus_constructor.system_bus()

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    self.stop()

  @ClassLogger.TraceAs.call(with_arguments = False)
  def start(self, name, pincode):
    if self.__started:
      return

    self.__adapter = Bluez5Utils.find_adapter(self.__hci_device, self.__bus)

    adapter_path = self.__adapter.object_path
    self.__adapter_properties = Bluez5Utils.properties(adapter_path, self.__bus)

    self.__bus.add_signal_receiver(
      self.properties_changed,
      dbus_interface = Bluez5Utils.PROPERTIES_INTERFACE,
      signal_name = 'PropertiesChanged',
      arg0 = Bluez5Utils.DEVICE_INTERFACE,
      path_keyword = 'path'
    )

    self.enable()

    if name:
      self.__set_property('Alias', name)

    self.__show_adapter_properties()

    self.log().info('Registering agent: ' + self.AGENT_PATH)
    self.__agent = PermissibleAgent(self.__bus, self.AGENT_PATH)
    self.__agent.set_pincode(pincode)

    self.__started = True

    self.__reestablish_device_connections()

  def stop(self):
    if not self.__started:
      return

    if self.pairable():
      self.disable_pairability()

    self.__started = False

  def enable(self):
    self.__set_property('Powered', True)

  def disable(self):
    self.__set_property('Powered', False)

  def enabled(self):
    return self.__get_property('Powered')

  @ClassLogger.TraceAs.event()
  def enable_pairability(self, timeout = 0):
    self.__set_property('Discoverable', True)
    self.__set_property('Pairable', True)
    self.__set_property('PairableTimeout', dbus.UInt32(timeout))
    self.__set_property('DiscoverableTimeout', dbus.UInt32(timeout))

  @ClassLogger.TraceAs.event()
  def disable_pairability(self):
    try:
      self.__set_property('Discoverable', False)
      self.__set_property('Pairable', False)
      self.__set_property('PairableTimeout', dbus.UInt32(0))
      self.__set_property('DiscoverableTimeout', dbus.UInt32(180))
    except:
      pass

  def pairable(self):
    return self.__get_property('Discoverable') and self.__get_property('Pairable')

  def hci_device(self):
    last_slash = self.__adapter.object_path.rfind('/')
    return self.__adapter.object_path[last_slash + 1:]

  def address(self):
    return self.__get_property('Address')

  def device_class(self):
    return self.__get_property('Class')

  @ClassLogger.TraceAs.call()
  def disconnect_device(self, path):
    pass

  @ClassLogger.TraceAs.call()
  def disconnect_all_devices(self):
    devices = self.__find_connected_devices()
    for device in devices:
      device.Disconnected()

  def on_device_connected(self, listener):
    self.__on_device_connected_listeners.append(listener)

  def on_device_disconnected(self, listener):
    self.__on_device_disconnected_listeners.append(listener)

  def properties_changed(self, interface, changed, invalidated, path):
    if interface == Bluez5Utils.DEVICE_INTERFACE:
      self.device_properties_changed(changed, path)

  def device_properties_changed(self, changed, path):
    if 'Connected' in changed:
      connected = changed['Connected']
      if connected:
        listeners = self.__on_device_connected_listeners
      else:
        listeners = self.__on_device_disconnected_listeners

      self.log().info('Device: ' + path + (' Connected' if connected else ' Disconnected'))

      for listener in listeners:
        listener(path)

  def __reestablish_device_connections(self):
    # This is mostly for development, in case the main application
    # is restarted after a device has already been paired and connected.
    already_connected = self.__find_connected_devices()

    self.log().info('Found %d device(s) already connected, Notifying...' % len(already_connected))

    for device in already_connected:
      for listener in self.__on_device_connected_listeners:
        listener(device.object_path)

  def __find_connected_devices(self):
    connected_devices = []

    devices = Bluez5Utils.get_known_devices(self.address(), self.__bus)
    for device in devices:
      """What a pain in the ass!"""
      properties = Bluez5Utils.properties(device.object_path, self.__bus)

      paired = properties.Get(Bluez5Utils.DEVICE_INTERFACE, 'Paired')
      connected = properties.Get(Bluez5Utils.DEVICE_INTERFACE, 'Connected')

      if paired and connected:
        connected_devices.append(device)

    return connected_devices

  def __show_adapter_properties(self):
    self.log().debug('Adapter Path: ' + self.__adapter.object_path)
    self.log().debug('Adapter HCI handle: ' + self.hci_device())
    self.log().debug('Adapter Name: ' + self.__get_property('Name'))
    self.log().debug('Adapter Alias: ' + self.__get_property('Alias'))
    self.log().debug('Adapter Address: ' + self.__get_property('Address'))
    self.log().debug('Adapter Class: 0x%06x' % self.__get_property('Class'))

  def __get_property(self, prop):
    return self.__adapter_properties.Get(Bluez5Utils.ADAPTER_INTERFACE, prop)

  def __set_property(self, prop, value):
    self.__adapter_properties.Set(Bluez5Utils.ADAPTER_INTERFACE, prop, value)

class PermissibleAgent(dbus.service.Object, ClassLogger):
  __passcode = None
  __pincode = None
  __path = None
  __capability = None

  def __init__(self, bus, path):
    ClassLogger.__init__(self)
    dbus.service.Object.__init__(self, bus, path)

    self.__path = path
    self.__capability = 'KeyboardDisplay'

    #
    # These profile modes appear to cause the agent to ignore
    # pin and passcode requests...
    #
    #self.__capability = 'NoInputNoOutput'
    #self.__capability = 'DisplayOnly'
    #self.__capability = 'KeyboardOnly'

    # Other types that seem to work
    #self.__capability = 'KeyboardDisplay'
    #self.__capability = 'DisplayYesNo'

    manager = dbus.Interface(
      bus.get_object(Bluez5Utils.SERVICE_NAME, '/org/bluez'),
      Bluez5Utils.AGENT_MANAGER_INTERFACE
    )

    manager.RegisterAgent(self.__path, self.__capability)
    manager.RequestDefaultAgent(self.__path)

  def set_pincode(self, pincode):
    self.__pincode = str(pincode)
    if len(self.__pincode) < 1 or len(self.__pincode) > 16:
      raise Exception('Pincode must be between 1 and 16 characters long')

  def set_passcode(self, passcode):
    self.__passcode = passcode

  def path(self):
    return self.__path

  def capability(self):
    return self.__capability

  @dbus.service.method("org.bluez.Agent1", in_signature="", out_signature="")
  def Release(self):
    self.log().info('Release')

  @dbus.service.method("org.bluez.Agent1", in_signature="os", out_signature="")
  def AuthorizeService(self, device, uuid):
    self.log().info("Authorize (%s, %s)" % (device, uuid))

  @dbus.service.method("org.bluez.Agent1", in_signature="o", out_signature="s")
  def RequestPinCode(self, device):
    self.log().info("RequestPinCode (%s)" % (device))
    return self.__pincode

  @dbus.service.method("org.bluez.Agent1", in_signature="o", out_signature="u")
  def RequestPasskey(self, device):
    self.log().info("RequestPasskey (%s)" % (device))
    return dbus.UInt32(self.__passcode)

  @dbus.service.method("org.bluez.Agent1", in_signature="ouq", out_signature="")
  def DisplayPasskey(self, device, passkey, entered):
    self.log().info("DisplayPasskey (%s, %06u entered %u)" % (device, passkey, entered))

  @dbus.service.method("org.bluez.Agent1", in_signature="os", out_signature="")
  def DisplayPinCode(self, device, pincode):
    self.log().info("DisplayPinCode (%s, %s)" % (device, pincode))

  @dbus.service.method("org.bluez.Agent1", in_signature="ou", out_signature="")
  def RequestConfirmation(self, device, passkey):
    self.log().info("RequestConfirmation (%s, %06d)" % (device, passkey))

  @dbus.service.method("org.bluez.Agent1", in_signature="o", out_signature="")
  def RequestAuthorization(self, device):
    self.log().info("RequestAuthorization (%s)" % (device))

  @dbus.service.method("org.bluez.Agent1", in_signature="", out_signature="")
  def Cancel(self):
    self.log().info("Cancel")

class Bluez5Utils:
  """bluez5-x.y/test/bluezutils.py"""

  SERVICE_NAME = 'org.bluez'
  ADAPTER_INTERFACE = 'org.bluez.Adapter1'
  DEVICE_INTERFACE = 'org.bluez.Device1'
  AGENT_MANAGER_INTERFACE = 'org.bluez.AgentManager1'

  OBJECT_MANAGER_INTERFACE = 'org.freedesktop.DBus.ObjectManager'
  PROPERTIES_INTERFACE = 'org.freedesktop.DBus.Properties'

  @staticmethod
  def get_managed_objects(bus):
    manager = dbus.Interface(
      bus.get_object(Bluez5Utils.SERVICE_NAME, '/'),
      Bluez5Utils.OBJECT_MANAGER_INTERFACE
    )
    return manager.GetManagedObjects()

  @staticmethod
  def find_adapter(pattern, bus):
    return Bluez5Utils.find_adapter_in_objects(
      Bluez5Utils.get_managed_objects(bus),
      pattern,
      bus
    )

  @staticmethod
  def find_adapter_in_objects(objects, pattern, bus):
    if pattern:
      pattern = pattern.upper()
    for path, ifaces in objects.iteritems():
      adapter = ifaces.get(Bluez5Utils.ADAPTER_INTERFACE)
      if adapter is None:
        continue
      address = adapter['Address'].upper()
      if not pattern or pattern == address or path.endswith(pattern):
        obj = bus.get_object(Bluez5Utils.SERVICE_NAME, path)
        return dbus.Interface(obj, Bluez5Utils.ADAPTER_INTERFACE)
    raise Exception('Bluetooth adapter not found: "' + \
      pattern if pattern else '*' + '"')

  @staticmethod
  def get_known_devices(adapter_pattern, bus):
    return Bluez5Utils.get_known_devices_in_objects(
      Bluez5Utils.get_managed_objects(bus),
      adapter_pattern,
      bus
    )

  @staticmethod
  def get_known_devices_in_objects(objects, adapter_pattern, bus):
    devices = []

    path_prefix = ''
    if adapter_pattern:
      adapter = Bluez5Utils.find_adapter_in_objects(objects, adapter_pattern, bus)
      path_prefix = adapter.object_path
    for path, ifaces in objects.iteritems():
      device = ifaces.get(Bluez5Utils.DEVICE_INTERFACE)
      if device is None:
        continue
      if path.startswith(path_prefix):
        obj = bus.get_object(Bluez5Utils.SERVICE_NAME, path)
        devices.append(dbus.Interface(obj, Bluez5Utils.DEVICE_INTERFACE))

    return devices

  @staticmethod
  def find_device(device_address, adapter_pattern, bus):
    return Bluez5Utils.find_device_in_objects(
      Bluez5Utils.get_managed_objects(bus),
      device_address,
      adapter_pattern,
      bus
    )

  @staticmethod
  def find_device_in_objects(objects, device_address, adapter_pattern, bus):
    path_prefix = ''
    if adapter_pattern:
      adapter = Bluez5Utils.find_adapter_in_objects(objects, adapter_pattern, bus)
      path_prefix = adapter.object_path
    for path, ifaces in objects.iteritems():
      device = ifaces.get(Bluez5Utils.DEVICE_INTERFACE)
      if device is None:
        continue
      if (device['Address'] == device_address and
              path.startswith(path_prefix)):
        obj = bus.get_object(Bluez5Utils.SERVICE_NAME, path)
        return dbus.Interface(obj, Bluez5Utils.DEVICE_INTERFACE)

    raise Exception('Bluetooth device not found')

  @staticmethod
  def properties(path, bus):
    return dbus.Interface(
      bus.get_object(Bluez5Utils.SERVICE_NAME, path),
      Bluez5Utils.PROPERTIES_INTERFACE
    )