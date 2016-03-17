import dbus
from dbus.mainloop.glib import DBusGMainLoop

"""
"""
class Hfp:
  #
  # These are the service and interface names exposed to dbus
  # by the hfpd (nohands) daemon.  @see hfconsole.in in the
  # source tree of the nohands project as a reference.
  #
  DBUS_SERVICE_NAME = 'org.freedesktop.DBus'
  DBUS_INTERFACE_DBUS = 'org.freedesktop.DBus'
  DBUS_INTERFACE_PROPERTIES = 'org.freedesktop.DBus.Properties'
  DBUS_BUS_OBJECT = '/org/freedesktop/DBus'
  HFPD_HANDSFREE_INTERFACE_NAME = 'net.sf.nohands.hfpd.HandsFree'
  HFPD_SOUNDIO_INTERFACE_NAME = 'net.sf.nohands.hfpd.SoundIo'
  HFPD_AUDIOGATEWAY_INTERFACE_NAME = 'net.sf.nohands.hfpd.AudioGateway'
  HFPD_SERVICE_NAME = 'net.sf.nohands.hfpd'
  HFPD_HANDSFREE_OBJECT = '/net/sf/nohands/hfpd'
  HFPD_SOUNDIO_OBJECT = '/net/sf/nohands/hfpd/soundio'

  # Only supports this version of hfpd
  HFPD_EXACT_VERSION = 4

  __started = False
  __bluetooth_available = False
  __log = None
  __dbus = None
  __dbus_controller = None
  __hfpd_interface = None
  __hfpd_properties = None
  __sound_io_interface = None
  __sound_io_properties = None
  __hfp_signal_handler = None

  def __init__(self, log):
    self.__log = log;
    self.__dbus = dbus.SessionBus(mainloop = DBusGMainLoop())

  def start(self):
    try:
      self.__dbus_controller = dbus.Interface(
        self.__dbus.get_object(
          self.DBUS_SERVICE_NAME,
          self.DBUS_BUS_OBJECT
        ),
        dbus_interface = self.DBUS_INTERFACE_DBUS
      )

    except dbus.exception.DBusException, (ex):
      self.fatal('Could not connect to D-Bus:\n%s' % str(ex))

    try:
      self.__hfpd_interface = dbus.Interface(
        self.__dbus.get_object(
          self.HFPD_SERVICE_NAME,
          self.HFPD_HANDSFREE_OBJECT
        ),
        dbus_interface = self.HFPD_HANDSFREE_INTERFACE_NAME
      )

      self.__hfpd_properties = dbus.Interface(
        self.__dbus.get_object(
          self.HFPD_SERVICE_NAME,
          self.HFPD_HANDSFREE_OBJECT
        ),
        dbus_interface = self.DBUS_INTERFACE_PROPERTIES
      )

      self.__sound_io_interface = dbus.Interface(
        self.__dbus.get_object(
          self.HFPD_SERVICE_NAME,
          self.HFPD_SOUNDIO_OBJECT
        ),
        dbus_interface = self.HFPD_SOUNDIO_INTERFACE_NAME
      )

      self.__sound_io_properties = dbus.Interface(
        self.__dbus.get_object(
          self.HFPD_SERVICE_NAME,
          self.HFPD_SOUNDIO_OBJECT
        ),
        dbus_interface = self.DBUS_INTERFACE_PROPERTIES
      )

    except dbus.exceptions.DBusException, (ex):
      self.fatal(
        'Could not connect to hfpd:\n%s\n\n'
        'Ensure that hfpd and its D-Bus '
        'service file are installed correctly.\n'
        'If the problem persists, try starting '
        'hfpd manually, e.g. \"hfpd\", or out of '
        'your build directory, e.g. '
        '\"hfpd/hfpd\"' % str(ex)
      )

    version = self.hfpd('Version')
    if (version != self.HFPD_EXACT_VERSION):
      # :-(
      self.fatal("Unsupported version of hfpd: %d" % version)

    self.__hfp_signal_handler = HfpSignalHandler(self, self.__hfpd_interface)

    self.log().info('Connected to Hfp service')
    self.__started = True

  def stop(self):
    pass

  def started(self):
    return self.__started

  def hfpd(self, name = None, value = None):
    if (value == None):
      return self.__hfpd_properties.Get(self.HFPD_HANDSFREE_INTERFACE_NAME, name)
    else:
      self.__hfpd_properties.Set(self.HFPD_HANDSFREE_INTERFACE_NAME, name, value)

  def enable(self):
    self.log().info('Bluetooth Enabled')
    self.__bluetooth_available = True

  def disable(self):
    self.log().info('Bluetooth Disabled')
    self.__bluetooth_available = False

  def enabled(self):
    return self.__bluetooth_available

  def fatal(self, msg):
    self.log().error(msg)
    raise Exception(msg)

  def log(self, className = 'Hfp'):
    return self.__log;

"""
"""
class HfpSignalHandler:
  __hfp = None

  def __init__(self, hfp, hfpd_interface):
    self.__hfp = hfp

    hfpd_interface.connect_to_signal('SystemStateChanged', self.system_state_changed)
    hfpd_interface.connect_to_signal('InquiryResult', self.inquiry_result)
    hfpd_interface.connect_to_signal('InquiryStateChanged', self.inquiry_state_changed)
    hfpd_interface.connect_to_signal('AudioGatewayAdded', self.audio_gateway_added)
    hfpd_interface.connect_to_signal('AudioGatewayRemoved', self.audio_gateway_removed)
    hfpd_interface.connect_to_signal('LogMessage', self.log_message)

  def system_state_changed(self, state):
    if not state:
      self.__hfp.disable()
    else:
      self.__hfp.enable()

  def inquiry_result(self, addr, devclass):
    self.log().info('Discovered ' + devclass + ' ' + addr)

  def inquiry_state_changed(self, state):
    pass

  def audio_gateway_added(self, audio_gateway_path):
    pass

  def audio_gateway_removed(self, audio_gateway_path):
    pass

  def log_message(self, level, msg):
    self.log().log(self.normalize_log_level(level), msg)

  def normalize_log_level(self, hfp_log_level):
    # TODO: actually normalize hfp_log_level to
    # CRITICAL  50
    # ERROR 40
    # WARNING 30
    # INFO  20
    # DEBUG 10
    # NOTSET  0
    return hfp_log_level

  def log(self, className = 'HfpSignalHandler'):
    return self.__hfp.log(className)