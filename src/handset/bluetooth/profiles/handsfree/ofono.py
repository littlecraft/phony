import dbus
from handset.base.log import ClassLogger, Levels

class Ofono(ClassLogger):
  SERVICE_NAME = 'org.ofono'
  MANAGER_INTERFACE = 'org.ofono.Manager'
  HFP_INTERFACE = 'org.ofono.Handsfree'

  __bus = None

  __manager = None
  __hfp = None

  __modem = None
  __path = None
  __properties = None

  __attached_listeners = []
  __detached_listeners = []

  def __init__(self, bus):
    ClassLogger.__init__(self)

    self.__bus = bus.system_bus()

  @ClassLogger.TraceAs.call()
  def start(self):
    self.__manager = dbus.Interface(
      self.__bus.get_object(self.SERVICE_NAME, '/'),
      self.MANAGER_INTERFACE
    )

  @ClassLogger.TraceAs.call()
  def stop(self):
    pass

  @ClassLogger.TraceAs.call()
  def attach(self, device_address):
    modems = self.__manager.GetModems()

    found_path = None
    found_properties = None

    for path, properties in modems:
      if path.endswith(device_address) and properties['Type'] == 'hfp':
        found_path = path
        found_properties = properties
        break

    if not found_path:
      raise Exception('Unable to attach HandsFree profile with ' + device_address)
      return

    self.log().info('Attaching to profile path: ' + found_path)

    self.__path = found_path
    self.__properties = found_properties

    self.__hfp = dbus.Interface(
      self.__bus.get_object(self.SERVICE_NAME, self.__path),
      self.HFP_INTERFACE
    )

    self.__show_device()

    for listener in self.__attached_listeners:
      listener(self.__path)

  @ClassLogger.TraceAs.event()
  def detach(self, device_address):
    if not self.__path:
      return

    for listener in self.__detached_listeners:
      listener(self.__path)

  def on_attached(self, listener):
    self.__attached_listeners.append(listener)

  def on_detached(self, listener):
    self.__detached_listeners.append(listener)

  def __show_device(self):
    self.log().info('Device Name: ' + self.__properties['Name'])
    self.log().info('Device Profile Type: ' + self.__properties['Type'])
    self.log().info('Device Online: %s' % self.__properties['Online'])

    ifaces = ''
    for iface in self.__properties['Interfaces']:
      ifaces += iface + ' '
    self.log().info('Device Interfaces: %s' % ifaces)

    features = ''
    for feature in self.__hfp.GetProperties()['Features']:
      features += feature + ' '
    self.log().info('Device HFP Features: %s' % features)

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    pass
