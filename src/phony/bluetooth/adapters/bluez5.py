import dbus

from phony.base import execute
from phony.base.log import ClassLogger

class Bluez5(ClassLogger):
  AGENT_PATH = '/phony/agent/bluez'
  _agent = None

  _adapter_address = None

  _bus = None

  _adapter = None
  _adapter_properties = None

  _on_device_connected_listeners = []
  _on_device_disconnected_listeners = []

  _started = False

  def __init__(self, bus_provider, adapter_address = None):
    ClassLogger.__init__(self)
    self._adapter_address = adapter_address
    self._bus = bus_provider.system_bus()

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    self.stop()

  @ClassLogger.TraceAs.call(with_arguments = False)
  def start(self, name, pincode):
    if self._started:
      return

    self._adapter = Bluez5Utils.find_adapter(self._adapter_address, self._bus)

    self._adapter_properties = Bluez5Utils.properties(
      self._adapter.object_path,
      self._bus
    )

    self._bus.add_signal_receiver(
      self.properties_changed,
      dbus_interface = Bluez5Utils.PROPERTIES_INTERFACE,
      signal_name = 'PropertiesChanged',
      arg0 = Bluez5Utils.DEVICE_INTERFACE,
      path_keyword = 'path'
    )

    self._bus.add_signal_receiver(
      self.interfaces_added,
      dbus_interface = Bluez5Utils.OBJECT_MANAGER_INTERFACE,
      signal_name = 'InterfacesAdded'
    )

    self._bus.add_signal_receiver(
      self.interfaces_removed,
      dbus_interface = Bluez5Utils.OBJECT_MANAGER_INTERFACE,
      signal_name = 'InterfacesRemoved'
    )

    if name:
      self._set_property('Alias', name)

    self._set_property('Powered', True)

    self._show_properties()

    self.log().debug('Registering agent: ' + self.AGENT_PATH)
    self._agent = PermissibleAgent(self._bus, self.AGENT_PATH)
    self._agent.set_pincode(pincode)

    self._started = True

    self._find_connected_devices_and_notify()

  def stop(self):
    if not self._started:
      return

    if self.pairable():
      self.disable_pairability()

    self.disconnect_all_devices()

    self._started = False

  @ClassLogger.TraceAs.call()
  def cancel_pending_operations(self):
    pass

  @ClassLogger.TraceAs.event()
  def enable_pairability(self, timeout = 0):
    self._set_property('Discoverable', True)
    self._set_property('Pairable', True)
    self._set_property('PairableTimeout', dbus.UInt32(timeout))
    self._set_property('DiscoverableTimeout', dbus.UInt32(timeout))

  @ClassLogger.TraceAs.event()
  def disable_pairability(self):
    try:
      self._set_property('Discoverable', False)
      self._set_property('Pairable', False)
      self._set_property('PairableTimeout', dbus.UInt32(0))
      self._set_property('DiscoverableTimeout', dbus.UInt32(180))
    except:
      pass

  def pairable(self):
    return self._get_property('Discoverable') and self._get_property('Pairable')

  def hci_id(self):
    last_slash = self._adapter.object_path.rfind('/')
    return self._adapter.object_path[last_slash + 1:]

  def address(self):
    return self._get_property('Address')

  @ClassLogger.TraceAs.call()
  def disconnect_all_devices(self):
    devices = self._find_connected_devices()
    for device in devices:
      device.disconnect()

  def on_device_connected(self, listener):
    self._on_device_connected_listeners.append(listener)

  def on_device_disconnected(self, listener):
    self._on_device_disconnected_listeners.append(listener)

  @ClassLogger.TraceAs.event()
  def properties_changed(self, interface, changed, invalidated, path):
    if interface != Bluez5Utils.DEVICE_INTERFACE:
      return

    if 'Connected' in changed:
      connected = changed['Connected']

      if connected:
        self.log().info('Device: %s Connected' % path)
        for listener in self._on_device_connected_listeners:
          device = Bluez5Utils.device(path, self._bus)
          device = Bluez5Device(device, self._bus)
          listener(device)
      else:
        self.log().info('Device: %s Disconnected' % path)
        for listener in self._on_device_disconnected_listeners:
          listener(path)

  @ClassLogger.TraceAs.event()
  def interfaces_added(self, path, interfaces):
    if Bluez5Utils.DEVICE_INTERFACE not in interfaces:
      return

    if Bluez5Utils.is_child_device(self._adapter, path):
      self.log().info('New device added: %s' % path)

      properties = interfaces[Bluez5Utils.DEVICE_INTERFACE]

      if 'Connected' in properties and properties['Connected']:
        for listener in self._on_device_connected_listeners:
          device = Bluez5Utils.device(path, self._bus)
          device = Bluez5Device(device, self._bus)
          listener(device)

  @ClassLogger.TraceAs.event()
  def interfaces_removed(self, path, interfaces):
    if Bluez5Utils.DEVICE_INTERFACE not in interfaces:
      return

    if Bluez5Utils.is_child_device(self._adapter, path):
      self.log().info('Device removed: %s' % path)

      for listener in self._on_device_disconnected_listeners:
        listener(path)

  def _find_connected_devices_and_notify(self):
    # This is mostly for development, in case the main application
    # is restarted after a device has already been paired and connected.
    already_connected = self._find_connected_devices()

    if len(already_connected) > 0:
      self.log().info('Found %d device(s) connected, notifying...' % len(already_connected))

    for device in already_connected:
      for listener in self._on_device_connected_listeners:
        listener(device)

  def _find_connected_devices(self):
    connected_devices = []

    devices = Bluez5Utils.get_child_devices(self.address(), self._bus)
    for device in devices:
      device = Bluez5Device(device, self._bus)

      if device.paired() and device.connected():
        connected_devices.append(device)

    return connected_devices

  def _show_properties(self):
    self.log().debug('Adapter Path: ' + self._adapter.object_path)
    self.log().debug('Adapter HCI Id: ' + self.hci_id())
    self.log().debug('Adapter Name: ' + self._get_property('Name'))
    self.log().debug('Adapter Alias: ' + self._get_property('Alias'))
    self.log().debug('Adapter Address: ' + self._get_property('Address'))
    self.log().debug('Adapter Class: 0x%06x' % self._get_property('Class'))

  def _get_property(self, prop):
    return self._adapter_properties.Get(Bluez5Utils.ADAPTER_INTERFACE, prop)

  def _set_property(self, prop, value):
    self._adapter_properties.Set(Bluez5Utils.ADAPTER_INTERFACE, prop, value)

  def __repr__(self):
    return '%s %s' % (self._get_property('Address'), self._get_property('Name'))

class PermissibleAgent(dbus.service.Object, ClassLogger):
  _passcode = None
  _pincode = None
  _path = None
  _capability = None

  def __init__(self, bus, path):
    ClassLogger.__init__(self)
    dbus.service.Object.__init__(self, bus, path)

    self._path = path
    self._capability = 'KeyboardDisplay'

    #
    # These profile modes appear to cause the agent to ignore
    # pin and passcode requests...
    #
    #self._capability = 'NoInputNoOutput'
    #self._capability = 'DisplayOnly'
    #self._capability = 'KeyboardOnly'

    # Other types that seem to work
    #self._capability = 'KeyboardDisplay'
    #self._capability = 'DisplayYesNo'

    manager = dbus.Interface(
      bus.get_object(Bluez5Utils.SERVICE_NAME, '/org/bluez'),
      Bluez5Utils.AGENT_MANAGER_INTERFACE
    )

    manager.RegisterAgent(self._path, self._capability)
    manager.RequestDefaultAgent(self._path)

  def set_pincode(self, pincode):
    self._pincode = str(pincode)
    if len(self._pincode) < 1 or len(self._pincode) > 16:
      raise Exception('Pincode must be between 1 and 16 characters long')

  def set_passcode(self, passcode):
    self._passcode = passcode

  def path(self):
    return self._path

  def capability(self):
    return self._capability

  @dbus.service.method("org.bluez.Agent1", in_signature="", out_signature="")
  def Release(self):
    self.log().debug('Release')

  @dbus.service.method("org.bluez.Agent1", in_signature="os", out_signature="")
  def AuthorizeService(self, device, uuid):
    self.log().debug("Authorize (%s, %s)" % (device, uuid))

  @dbus.service.method("org.bluez.Agent1", in_signature="o", out_signature="s")
  def RequestPinCode(self, device):
    self.log().debug("RequestPinCode (%s)" % (device))
    return self._pincode

  @dbus.service.method("org.bluez.Agent1", in_signature="o", out_signature="u")
  def RequestPasskey(self, device):
    self.log().debug("RequestPasskey (%s)" % (device))
    return dbus.UInt32(self._passcode)

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
      if not pattern or pattern == address or path.upper().endswith(pattern):
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
  _device = None
  _properties = None
  _bus = None

  def __init__(self, device, bus):
    ClassLogger.__init__(self)

    self._device = device
    self._bus = bus

    self._properties = Bluez5Utils.properties(device.object_path, self._bus)

  @ClassLogger.TraceAs.call()
  def dispose(self):
    try:
      self.disconnect()
    except Exception:
      pass

  @ClassLogger.TraceAs.call()
  def disconnect(self):
    if self.connected():
      return self._device.Disconnect()

  def path(self):
    return self._device.object_path

  def address(self):
    return self._get_property('Address')

  def name(self):
    return self._get_property('Name')

  def connected(self):
    return self._get_property('Connected')

  def paired(self):
    return self._get_property('Paired')

  def _get_property(self, prop):
    return self._properties.Get(Bluez5Utils.DEVICE_INTERFACE, prop)

  def _set_property(self, prop, value):
    self._properties.Set(Bluez5Utils.DEVICE_INTERFACE, prop, value)

  def __repr__(self):
    return '%s %s' % (self.address(), self.name())

  def __eq__(self, other):
    return (isinstance(other, self.__class__)
      and self.address() == other.address())