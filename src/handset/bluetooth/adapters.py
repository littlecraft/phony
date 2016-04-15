import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
from handset.base.log import ClassLogger

class Bluez4(ClassLogger):
  DBUS_SERVICE_NAME = 'org.bluez'
  DBUS_BUS_OBJECT = '/'
  DBUS_MANAGER_INTERFACE = 'org.bluez.Manager'
  DBUS_ADAPTER_INTERFACE = 'org.bluez.Adapter'
  DBUS_DEVICE_INTERFACE = 'org.bluez.Device'

  __bus = None

  __hci_device = None

  __adapter_path = None
  __adapter = None
  __adapter_signal_handler = None

  __agent = None

  __started = False

  def __init__(self, hci_device):
    ClassLogger.__init__(self)
    self.__hci_device = hci_device

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    pass

  @ClassLogger.TraceAs.call(with_arguments = False)
  def start(self, name, pincode):
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

    self.__adapter = dbus.Interface(
      self.__bus.get_object(
        self.DBUS_SERVICE_NAME,
        self.__adapter_path
      ),
      dbus_interface = self.DBUS_ADAPTER_INTERFACE
    )
    self.__adapter_signal_handler = Bluez4AdapterSignalHandler(self)

    agent_path = '/farmfone/agent'
    self.__agent = Bluez4PermissibleAgent(self, agent_path)
    self.__agent.set_pincode(pincode);

    self.set_property('Name', name)

    self.__started = True

    self.show_device_properties()

  def show_device_properties(self):
    self.log().debug('Adapter device id: ' + self.device_id())
    self.log().debug('Adapter name: ' + self.name())
    self.log().debug('Adapter address: ' + self.address())
    self.log().debug('Adapter class: ' + str(self.get_property('Class')))

  def stop(self):
    if self.visible():
      self.disable_visibility()

  def bound_devices(self):
    devices = []
    for device_path in self.adapter().ListDevices():
      device = self.get_device(device_path)
      if (device.get_property('Paired')):
        devices.append(device)

    return devices

  def enable(self):
    self.set_property('Powered', True)

  def disable(self):
    self.set_property('Powered', False)

  def enabled(self):
    return set.get_property('Powered')

  def enable_visibility(self):
    self.set_property('Discoverable', True)
    self.set_property('Pairable', True)
    self.__adapter.StartDiscovery()

  def disable_visibility(self):
    self.set_property('Discoverable', True)
    self.set_property('Pairable', True)
    self.__adapter.StopDiscovery()

  def visible(self):
    return self.get_property('Discoverable') and self.get_property('Pairable')

  def device_id(self):
    return self.__adapter_path

  def name(self):
    return self.get_property('Name')

  def address(self):
    return self.get_property('Address')

  def agent(self):
    return self.__agent

  def adapter(self):
    return self.__adapter

  def bus(self):
    return self.__bus

  def set_property(self, name, value):
    self.__adapter.SetProperty(name, value)

  def get_property(self, name):
    properties = self.__adapter.GetProperties()
    return properties[name]

  def get_device(self, device_path):
    return Bluez4Device(
      dbus.Interface(
        self.__bus.get_object(
          self.DBUS_SERVICE_NAME,
          device_path
        ),
        dbus_interface = self.DBUS_DEVICE_INTERFACE
      )
    )

class Bluez4AdapterSignalHandler(ClassLogger):
  __bluez4 = None

  def __init__(self, bluez4):
    ClassLogger.__init__(self)
    self.__bluez4 = bluez4

    adapter = bluez4.adapter()
    adapter.connect_to_signal('PropertyChanged', self.property_changed)
    adapter.connect_to_signal('DeviceFound', self.device_found)
    adapter.connect_to_signal('DeviceDisappeared', self.device_disappeared)
    adapter.connect_to_signal('DeviceCreated', self.device_created)
    adapter.connect_to_signal('DeviceRemoved', self.device_removed)

  #@ClassLogger.TraceAs.event()
  def property_changed(self, name, value):
    pass

  @ClassLogger.TraceAs.event()
  def device_found(self, address, properties):
    pass
    #try:
    #  self.__bluez4.adapter().CreateDevice(address)
    #except dbus.DBusException, ex:
    #  if ex.get_dbus_name() != 'org.bluez.Error.AlreadyExists':
    #    self.log().error('Unable to create device for ' + str(address) + str(ex))
    #  else:
    #    self.log().debug('Device already exists for ' + str(address))
    #self.__bluez4.adapter().CreatePairedDevice(
    #  str(address),
    #  self.__bluez4.agent().path(),
    #  self.__bluez4.agent().capability(),
    #  timeout = 60000,
    #  reply_handler = create_device_reply,
    #  error_handler = create_device_error
    #)

  #def create_device_reply(device):
  #  pass

  #def create_device_error(error):
  #  pass

  @ClassLogger.TraceAs.event()
  def device_disappeared(self, address):
    pass

  @ClassLogger.TraceAs.event()
  def device_created(self, device):
    pass

  @ClassLogger.TraceAs.event()
  def device_removed(self, device):
    pass

class Rejected(dbus.DBusException):
  _dbus_error_name = "org.bluez.Error.Rejected"

# except dbus.DbusException, ex:
#   if ex.get_dbus_name() == 'path.to.dbus.exception.name':

class Bluez4PermissibleAgent(dbus.service.Object, ClassLogger):
  __passcode = None
  __pincode = None
  __path = None
  __capability = None

  def __init__(self, bluez4, path):
    ClassLogger.__init__(self)
    dbus.service.Object.__init__(self, bluez4.bus(), path)

    self.__path = path
    self.__capability = 'NoInputNoOutput'

    bluez4.adapter().RegisterAgent(path, self.__capability)

  def set_pincode(self, pincode):
    self.__pincode = pincode

  def set_passcode(self, passcode):
    self.__passcode = passcode

  def path(self):
    return self.__path

  def capability(self):
    return self.__capability

  @dbus.service.method("org.bluez.Agent", in_signature="", out_signature="")
  def Release(self):
    self.log().debug('Release')

  @dbus.service.method("org.bluez.Agent", in_signature="os", out_signature="")
  def Authorize(self, device, uuid):
    self.log().debug("Authorize (%s, %s)" % (device, uuid))

  @dbus.service.method("org.bluez.Agent", in_signature="o", out_signature="s")
  def RequestPinCode(self, device):
    self.log().debug("RequestPinCode (%s)" % (device))
    return str(self.__pincode)

  @dbus.service.method("org.bluez.Agent", in_signature="o", out_signature="u")
  def RequestPasskey(self, device):
    self.log().debug("RequestPasskey (%s)" % (device))
    return dbus.UInt32(self.__passcode)

  @dbus.service.method("org.bluez.Agent", in_signature="ouq", out_signature="")
  def DisplayPasskey(self, device, passkey, entered):
    self.log().debug("DisplayPasskey (%s, %06u entered %u)" % (device, passkey, entered))

  @dbus.service.method("org.bluez.Agent", in_signature="os", out_signature="")
  def DisplayPinCode(self, device, pincode):
    self.log().debug("DisplayPinCode (%s, %s)" % (device, pincode))

  @dbus.service.method("org.bluez.Agent", in_signature="ou", out_signature="")
  def RequestConfirmation(self, device, passkey):
    self.log().debug("RequestConfirmation (%s, %06d)" % (device, passkey))

  @dbus.service.method("org.bluez.Agent", in_signature="s", out_signature="")
  def ConfirmModeChange(self, mode):
    self.log().debug("ConfirmModeChange (%s)" % (mode))

  @dbus.service.method("org.bluez.Agent", in_signature="", out_signature="")
  def Cancel(self):
    self.log().debug("Cancel")

class Bluez4Device(ClassLogger):
  __device = None

  def __init__(self, device):
    self.__device = device

  def get_property(self, name):
    return self.__device.GetProperties()[name]

  def __repr__(self):
    return self.get_property('Address')