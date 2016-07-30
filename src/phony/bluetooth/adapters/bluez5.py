import dbus

from phony.base import execute
from phony.base.log import ClassLogger

class Bluez5(ClassLogger):
  AGENT_PATH = '/phony/agent/bluez'
  __agent = None

  __adapter_address = None

  __bus = None

  __adapter = None
  __adapter_properties = None

  __on_device_connected_listeners = []
  __on_device_disconnected_listeners = []

  __started = False

  def __init__(self, bus_constructor, adapter_address = None):
    ClassLogger.__init__(self)
    self.__adapter_address = adapter_address
    self.__bus = bus_constructor.system_bus()

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    self.stop()

  @ClassLogger.TraceAs.call(with_arguments = False)
  def start(self, name, pincode):
    if self.__started:
      return

    self.__adapter = Bluez5Utils.find_adapter(self.__adapter_address, self.__bus)

    self.__adapter_properties = Bluez5Utils.properties(
      self.__adapter.object_path,
      self.__bus
    )

    self.__bus.add_signal_receiver(
      self.properties_changed,
      dbus_interface = Bluez5Utils.PROPERTIES_INTERFACE,
      signal_name = 'PropertiesChanged',
      arg0 = Bluez5Utils.DEVICE_INTERFACE,
      path_keyword = 'path'
    )

    self.__bus.add_signal_receiver(
      self.interfaces_added,
      dbus_interface = Bluez5Utils.OBJECT_MANAGER_INTERFACE,
      signal_name = 'InterfacesAdded'
    )

    self.__bus.add_signal_receiver(
      self.interfaces_removed,
      dbus_interface = Bluez5Utils.OBJECT_MANAGER_INTERFACE,
      signal_name = 'InterfacesRemoved'
    )

    if name:
      self.__set_property('Alias', name)

    self.__set_property('Powered', True)

    self.__show_adapter_properties()

    self.log().info('Registering agent: ' + self.AGENT_PATH)
    self.__agent = PermissibleAgent(self.__bus, self.AGENT_PATH)
    self.__agent.set_pincode(pincode)

    self.__started = True

    self.__find_connected_devices_and_notify()

  def stop(self):
    if not self.__started:
      return

    if self.pairable():
      self.disable_pairability()

    self.disconnect_all_devices()

    self.__started = False

  @ClassLogger.TraceAs.call()
  def cancel_pending_operations(self):
    pass

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

  def hci_id(self):
    last_slash = self.__adapter.object_path.rfind('/')
    return self.__adapter.object_path[last_slash + 1:]

  def address(self):
    return self.__get_property('Address')

  @ClassLogger.TraceAs.call()
  def disconnect_all_devices(self):
    devices = self.__find_connected_devices()
    for device in devices:
      device.disconnect()

  def on_device_connected(self, listener):
    self.__on_device_connected_listeners.append(listener)

  def on_device_disconnected(self, listener):
    self.__on_device_disconnected_listeners.append(listener)

  @ClassLogger.TraceAs.event()
  def properties_changed(self, interface, changed, invalidated, path):
    if interface != Bluez5Utils.DEVICE_INTERFACE:
      return

    if 'Connected' in changed:
      connected = changed['Connected']

      if connected:
        self.log().info('Device: %s Connected' % path)
        for listener in self.__on_device_connected_listeners:
          device = Bluez5Utils.device(path, self.__bus)
          device = Bluez5Device(device, self.__bus)
          listener(device)
      else:
        self.log().info('Device: %s Disconnected' % path)
        for listener in self.__on_device_disconnected_listeners:
          listener(path)

  @ClassLogger.TraceAs.event()
  def interfaces_added(self, path, interfaces):
    if Bluez5Utils.DEVICE_INTERFACE not in interfaces:
      return

    if Bluez5Utils.is_child_device(self.__adapter, path):
      self.log().info('New device added: %s' % path)

      properties = interfaces[Bluez5Utils.DEVICE_INTERFACE]

      if 'Connected' in properties and properties['Connected']:
        for listener in self.__on_device_connected_listeners:
          device = Bluez5Utils.device(path, self.__bus)
          device = Bluez5Device(device, self.__bus)
          listener(device)

  @ClassLogger.TraceAs.event()
  def interfaces_removed(self, path, interfaces):
    if Bluez5Utils.DEVICE_INTERFACE not in interfaces:
      return

    if Bluez5Utils.is_child_device(self.__adapter, path):
      self.log().info('Device removed: %s' % path)

      for listener in self.__on_device_disconnected_listeners:
        listener(path)

  def __find_connected_devices_and_notify(self):
    # This is mostly for development, in case the main application
    # is restarted after a device has already been paired and connected.
    already_connected = self.__find_connected_devices()

    if len(already_connected) > 0:
      self.log().info('Found %d device(s) connected, notifying...' % len(already_connected))

    for device in already_connected:
      for listener in self.__on_device_connected_listeners:
        listener(device)

  def __find_connected_devices(self):
    connected_devices = []

    devices = Bluez5Utils.get_child_devices(self.address(), self.__bus)
    for device in devices:
      device = Bluez5Device(device, self.__bus)

      if device.paired() and device.connected():
        connected_devices.append(device)

    return connected_devices

  def __show_adapter_properties(self):
    self.log().debug('Adapter Path: ' + self.__adapter.object_path)
    self.log().debug('Adapter HCI Id: ' + self.hci_id())
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
    self.log().debug('Release')

  @dbus.service.method("org.bluez.Agent1", in_signature="os", out_signature="")
  def AuthorizeService(self, device, uuid):
    self.log().debug("Authorize (%s, %s)" % (device, uuid))

  @dbus.service.method("org.bluez.Agent1", in_signature="o", out_signature="s")
  def RequestPinCode(self, device):
    self.log().debug("RequestPinCode (%s)" % (device))
    return self.__pincode

  @dbus.service.method("org.bluez.Agent1", in_signature="o", out_signature="u")
  def RequestPasskey(self, device):
    self.log().debug("RequestPasskey (%s)" % (device))
    return dbus.UInt32(self.__passcode)

  @dbus.service.method("org.bluez.Agent1", in_signature="ouq", out_signature="")
  def DisplayPasskey(self, device, passkey, entered):
    self.log().debug("DisplayPasskey (%s, %06u entered %u)" % (device, passkey, entered))

  @dbus.service.method("org.bluez.Agent1", in_signature="os", out_signature="")
  def DisplayPinCode(self, device, pincode):
    self.log().debug("DisplayPinCode (%s, %s)" % (device, pincode))

  @dbus.service.method("org.bluez.Agent1", in_signature="ou", out_signature="")
  def RequestConfirmation(self, device, passkey):
    self.log().debug("RequestConfirmation (%s, %06d)" % (device, passkey))

  @dbus.service.method("org.bluez.Agent1", in_signature="o", out_signature="")
  def RequestAuthorization(self, device):
    self.log().debug("RequestAuthorization (%s)" % (device))

  @dbus.service.method("org.bluez.Agent1", in_signature="", out_signature="")
  def Cancel(self):
    self.log().debug("Cancel")

class Bluez5Utils:
  """See bluez5-x.y/test/bluezutils.py"""

  SERVICE_NAME = 'org.bluez'
  ADAPTER_INTERFACE = 'org.bluez.Adapter1'
  DEVICE_INTERFACE = 'org.bluez.Device1'
  AGENT_MANAGER_INTERFACE = 'org.bluez.AgentManager1'

  OBJECT_MANAGER_INTERFACE = 'org.freedesktop.DBus.ObjectManager'
  PROPERTIES_INTERFACE = 'org.freedesktop.DBus.Properties'

  class UUID:
    """Service UUIDs that a device may provide"""

    Base = '00000000-0000-1000-8000-00805F9B34FB'
    HandsFree = '0000111E-0000-1000-8000-00805F9B34FB'
    HandsFreeAudioGateway = '0000111F-0000-1000-8000-00805F9B34FB'

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
        return Bluez5Utils.adapter(path, bus)

    raise Exception('Bluetooth adapter not found: "' + \
      pattern if pattern else '*' + '"')

  @staticmethod
  def get_child_devices(adapter_pattern, bus):
    return Bluez5Utils.get_child_devices_in_objects(
      Bluez5Utils.get_managed_objects(bus),
      adapter_pattern,
      bus
    )

  @staticmethod
  def get_child_devices_in_objects(objects, adapter_pattern, bus):
    devices = []

    adapter = None
    if adapter_pattern:
      adapter = Bluez5Utils.find_adapter_in_objects(objects, adapter_pattern, bus)
      if not adapter:
        raise Exception('Adapter not found by pattern "%s"' % adapter_pattern)

    for path, ifaces in objects.iteritems():
      device = ifaces.get(Bluez5Utils.DEVICE_INTERFACE)

      if device is None:
        continue

      if not adapter or Bluez5Utils.is_child_device(adapter, path):
        devices.append(Bluez5Utils.device(path, bus))

    return devices

  @staticmethod
  def is_child_device(adapter, device_path):
    return device_path.startswith(adapter.object_path)

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
        return Bluez5Utils.device(path, bus)

    raise Exception('Bluetooth device not found')

  @staticmethod
  def properties(path, bus):
    return dbus.Interface(
      bus.get_object(Bluez5Utils.SERVICE_NAME, path),
      Bluez5Utils.PROPERTIES_INTERFACE
    )

  @staticmethod
  def device(path, bus):
    return dbus.Interface(
      bus.get_object(Bluez5Utils.SERVICE_NAME, path),
      Bluez5Utils.DEVICE_INTERFACE
    )

  @staticmethod
  def adapter(path, bus):
    return dbus.Interface(
      bus.get_object(Bluez5Utils.SERVICE_NAME, path),
      Bluez5Utils.ADAPTER_INTERFACE
    )

class Bluez5Device(ClassLogger):
  __device = None
  __properties = None
  __bus = None

  def __init__(self, device, bus):
    ClassLogger.__init__(self)

    self.__device = device
    self.__bus = bus

    self.__properties = Bluez5Utils.properties(device.object_path, self.__bus)

  @ClassLogger.TraceAs.call()
  def dispose(self):
    try:
      self.disconnect()
    except Exception:
      pass

  @ClassLogger.TraceAs.call()
  def disconnect(self):
    if self.connected():
      return self.__device.Disconnect()

  def path(self):
    return self.__device.object_path

  def address(self):
    return self.__get_property('Address')

  def name(self):
    return self.__get_property('Name')

  def connected(self):
    return self.__get_property('Connected')

  def paired(self):
    return self.__get_property('Paired')

  def __get_property(self, prop):
    return self.__properties.Get(Bluez5Utils.DEVICE_INTERFACE, prop)

  def __set_property(self, prop, value):
    self.__properties.Set(Bluez5Utils.DEVICE_INTERFACE, prop, value)

  def __repr__(self):
    return '%s %s' % (self.address(), self.name())

  def __eq__(self, other):
    return (isinstance(other, self.__class__)
      and self.address() == other.address())