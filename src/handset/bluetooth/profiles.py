import dbus
import handset.base.log
from dbus.mainloop.glib import DBusGMainLoop
from handset.base.log import ClassLogger

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

  def started(self):
    return self.__started

  def stop(self):
    pass

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
    hfpd_interface.connect_to_signal('AudioGatewayAdded', self.audio_gateway_added)
    hfpd_interface.connect_to_signal('AudioGatewayRemoved', self.audio_gateway_removed)
    hfpd_interface.connect_to_signal('LogMessage', self.log_message)

  @ClassLogger.TraceAs.event
  def system_state_changed(self, state):
    if not state:
      self.log().info('Bluetooth disabled')
    else:
      self.log().info('Bluetooth enabled')

  @ClassLogger.TraceAs.event
  def audio_gateway_added(self, audio_gateway_path):
    pass

  @ClassLogger.TraceAs.event
  def audio_gateway_removed(self, audio_gateway_path):
    pass

  def log_message(self, level, msg):
    self.log().log(self.__normalize_log_level(level), msg)

  def __normalize_log_level(self, hfp_log_level):
    if hfp_log_level == 50:
      return handset.base.log.Levels.CRITICAL
    elif hfp_log_level == 40:
      return handset.base.log.Levels.ERROR
    elif hfp_log_level == 30:
      return handset.base.log.Levels.WARNING
    elif hfp_log_level == 20:
      return handset.base.log.Levels.INFO
    elif hfp_log_level == 10:
      return handset.base.log.Levels.DEBUG
    else:
      return handset.base.log.Levels.DEFAULT