import dbus
from dbus.mainloop.glib import DBusGMainLoop
from base.log import ClassLogger
from base.log import Levels
from base.log import ClassMethodLogger

class HandsFree(ClassLogger):
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
  __scanning = False

  __dbus = None
  __dbus_controller = None
  __hfpd_interface = None
  __hfpd_properties = None
  __sound_io_interface = None
  __sound_io_properties = None

  __dbus_signal_handler = None
  __hfp_signal_handler = None

  def __init__(self):
    ClassLogger.__init__(self)

    main_loop = DBusGMainLoop()
    self.__dbus = dbus.SessionBus(mainloop = main_loop)

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    self.stop()

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

    self.__dbus_signal_handler = DbusSignalHandler(self, self.__dbus_controller)
    self.__hfp_signal_handler = HfpSignalHandler(self, self.__hfpd_interface)

    self.log().info('Connected to Hfp service')
    self.__started = True

  def stop(self):
    self.stop_scan()

  def started(self):
    return self.__started

  def enable(self):
    self.log().info('Bluetooth Enabled')
    self.__bluetooth_available = True

  def disable(self):
    self.log().info('Bluetooth Disabled')
    self.__bluetooth_available = False

  def enabled(self):
    return self.__bluetooth_available

  def scan(self):
    if not self.__scanning:
      self.__hfpd_interface.StartInquiry()

  def stop_scan(self):
    if self.__scanning:
      self.__hfpd_interface.StopInquiry()

  def scanning(self):
    return self.__scanning

  def scanning_began(self):
    self.__scanning = True

  def scanning_completed(self):
    self.__scanning = False

  def hfpd(self, name = None, value = None):
    if (value == None):
      return self.__hfpd_properties.Get(self.HFPD_HANDSFREE_INTERFACE_NAME, name)
    else:
      self.__hfpd_properties.Set(self.HFPD_HANDSFREE_INTERFACE_NAME, name, value)

  def fatal(self, msg):
    self.log().error(msg)
    raise Exception(msg)

class DbusSignalHandler(ClassLogger):
  __hfp = None

  def __init__(self, hfp, dbus_controller):
    ClassLogger.__init__(self)

    self.__hfp = hfp

    dbus_controller.connect_to_signal("NameOwnerChanged", self.name_owner_changed)

  def name_owner_changed(self, name, old_owner, new_owner):
    if name != self.__hfp.HFPD_SERVICE_NAME or new_owner != '':
      return
    self.__hfp.disable()

class HfpSignalHandler(ClassLogger):
  __hfp = None

  def __init__(self, hfp, hfpd_interface):
    ClassLogger.__init__(self)

    self.__hfp = hfp

    hfpd_interface.connect_to_signal('SystemStateChanged', self.system_state_changed)
    hfpd_interface.connect_to_signal('InquiryResult', self.inquiry_result)
    hfpd_interface.connect_to_signal('InquiryStateChanged', self.inquiry_state_changed)
    hfpd_interface.connect_to_signal('AudioGatewayAdded', self.audio_gateway_added)
    hfpd_interface.connect_to_signal('AudioGatewayRemoved', self.audio_gateway_removed)
    hfpd_interface.connect_to_signal('LogMessage', self.log_message)

  @ClassLogger.event
  def system_state_changed(self, state):
    if not state:
      self.__hfp.disable()
    else:
      self.__hfp.enable()

  @ClassLogger.event
  def inquiry_result(self, addr, devclass):
    self.log().info('Discovered ' + str(devclass) + ' ' + str(addr))

  @ClassLogger.event
  def inquiry_state_changed(self, began):
    began_or_completed = ''

    if began:
      began_or_completed = 'began'
      self.__hfp.scanning_began()
    else:
      began_or_completed = 'completed'
      self.__hfp.scanning_completed()

    self.log().info('Inquiry (scanning) ' + began_or_completed)

  @ClassLogger.event
  def audio_gateway_added(self, audio_gateway_path):
    pass

  @ClassLogger.event
  def audio_gateway_removed(self, audio_gateway_path):
    pass

  def log_message(self, level, msg):
    self.log().log(self.__normalize_log_level(level), msg)

  def __normalize_log_level(self, hfp_log_level):
    if hfp_log_level == 50:
      return Levels.CRITICAL
    elif hfp_log_level == 40:
      return Levels.ERROR
    elif hfp_log_level == 30:
      return Levels.WARNING
    elif hfp_log_level == 20:
      return Levels.INFO
    elif hfp_log_level == 10:
      return Levels.DEBUG
    else:
      return Levels.DEFAULT