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

  __bus = None
  __dbus_interface = None
  __hfpd_interface = None
  __hfpd_properties = None
  __sound_io_interface = None
  __sound_io_properties = None

  __dbus_signal_handler = None
  __hfp_signal_handler = None

  __audio_gateways = {}

  def __init__(self):
    ClassLogger.__init__(self)

    main_loop = DBusGMainLoop()
    self.__bus = dbus.SessionBus(mainloop = main_loop)

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    pass
    #self.stop()

  @ClassLogger.TraceAs.call()
  def start(self):
    try:
      self.__dbus_interface = dbus.Interface(
        self.__bus.get_object(
          self.DBUS_SERVICE_NAME,
          self.DBUS_BUS_OBJECT
        ),
        dbus_interface = self.DBUS_INTERFACE_DBUS
      )

    except dbus.exception.DBusException, (ex):
      self.__fatal('Could not connect to D-Bus:\n%s' % str(ex))

    try:
      self.__hfpd_interface = dbus.Interface(
        self.__bus.get_object(
          self.HFPD_SERVICE_NAME,
          self.HFPD_HANDSFREE_OBJECT
        ),
        dbus_interface = self.HFPD_HANDSFREE_INTERFACE_NAME
      )

      self.__hfpd_properties = dbus.Interface(
        self.__bus.get_object(
          self.HFPD_SERVICE_NAME,
          self.HFPD_HANDSFREE_OBJECT
        ),
        dbus_interface = self.DBUS_INTERFACE_PROPERTIES
      )

      self.__sound_io_interface = dbus.Interface(
        self.__bus.get_object(
          self.HFPD_SERVICE_NAME,
          self.HFPD_SOUNDIO_OBJECT
        ),
        dbus_interface = self.HFPD_SOUNDIO_INTERFACE_NAME
      )

      self.__sound_io_properties = dbus.Interface(
        self.__bus.get_object(
          self.HFPD_SERVICE_NAME,
          self.HFPD_SOUNDIO_OBJECT
        ),
        dbus_interface = self.DBUS_INTERFACE_PROPERTIES
      )

    except dbus.exceptions.DBusException, (ex):
      self.__fatal(
        'Could not connect to hfpd:\n%s\n\n'
        'Ensure that hfpd and its D-Bus '
        'service file are installed correctly.\n'
        'If the problem persists, try starting '
        'hfpd manually, e.g. \"hfpd\", or out of '
        'your build directory, e.g. '
        '\"hfpd/hfpd\"' % str(ex)
      )

    version = self.get_property('Version')
    if (version != self.HFPD_EXACT_VERSION):
      self.__fatal("Unsupported version of hfpd: %d" % version)

    self.__dbus_signal_handler = HfpDbusSignalHandler(self)
    self.__hfp_signal_handler = HfpSignalHandler(self)

    self.log().info('Connected to Hfp service')

    self.hfpd().Start()

    self.__started = True

  def started(self):
    return self.__started

  @ClassLogger.TraceAs.call()
  def stop(self):
    pass

  @ClassLogger.TraceAs.call()
  def attach(self, address):
    try:
      # AudioGateway is constructed via AudioGatewayAdded signal handler
      audio_gateway_path = self.hfpd().AddDevice(address, False)
    except Exception, ex:
      self.log().error('Could not attach device ' + str(address) + ' : ' + str(ex))

  def add_audio_gateway(self, audio_gateway_path):
    if str(audio_gateway_path) not in self.__audio_gateways:
      ag = HfpAudioGateway(self, audio_gateway_path)
      ag.start()
      self.__audio_gateways[str(audio_gateway_path)] = ag

  def remove_audio_gateway(self, audio_gateway_path):
    if audio_gateway_path in self.__audio_gateways:
      del self.__audio_gateways[audio_gateway_path]

  def get_property(self, name):
    return self.__hfpd_properties.Get(self.HFPD_HANDSFREE_INTERFACE_NAME, name)

  def set_property(self, name, value):
    self.__hfpd_properties.Set(self.HFPD_HANDSFREE_INTERFACE_NAME, name, value)

  def hfpd(self):
    return self.__hfpd_interface

  def dbus_interface(self):
    return self.__dbus_interface

  def bus(self):
    return self.__bus

  def __fatal(self, msg):
    self.log().error(msg)
    raise Exception(msg)

class HfpDbusSignalHandler(ClassLogger):
  __hfp = None

  def __init__(self, hfp):
    ClassLogger.__init__(self)

    self.__hfp = hfp
    hfp.dbus_interface().connect_to_signal("NameOwnerChanged", self.name_owner_changed)

  def name_owner_changed(self, name, old_owner, new_owner):
    if name != self.__hfp.HFPD_SERVICE_NAME or new_owner != '':
      return

    self.log().debug('hfpd service disappeared, stopping');
    self.__hfp.stop()

class HfpSignalHandler(ClassLogger):
  __hfp = None

  def __init__(self, hfp):
    ClassLogger.__init__(self)

    self.__hfp = hfp

    hfp.hfpd().connect_to_signal('SystemStateChanged', self.system_state_changed)
    hfp.hfpd().connect_to_signal('AudioGatewayAdded', self.audio_gateway_added)
    hfp.hfpd().connect_to_signal('AudioGatewayRemoved', self.audio_gateway_removed)
    hfp.hfpd().connect_to_signal('LogMessage', self.log_message)

  @ClassLogger.TraceAs.event()
  def system_state_changed(self, state):
    pass

  @ClassLogger.TraceAs.event()
  def audio_gateway_added(self, audio_gateway_path):
    self.__hfp.add_audio_gateway(audio_gateway_path)

  @ClassLogger.TraceAs.event()
  def audio_gateway_removed(self, audio_gateway_path):
    self.__hfp.remove_audio_gateway(audio_gateway_path)

  def log_message(self, level, msg):
    self.log().log(self.__normalize_log_level(level), 'HFPD: ' +  msg)

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

class HfpAudioGateway(ClassLogger):
  # @see nohands/hfpd/proto.h
  class CallState:
    INVALID = 0
    IDLE = 1
    CONNECTING = 2
    ESTABLISHED = 3
    WAITING = 4
    ESTABLISHED_WAITING = 5

  class GatewayState:
    INVALID = 0
    DESTROYED = 1
    DISCONNECTED = 2
    CONNECTING = 3
    CONNECTED = 4

  class AudioState:
    INVALID = 0
    DISCONNECTED = 1
    CONNECTING = 2
    CONNECTED = 3

  __hfp = None
  __ag_interface = None
  __ag_properties = None
  __path = None

  def __init__(self, hfp, audio_gateway_path):
    ClassLogger.__init__(self)

    self.__hfp = hfp

    self.__path = audio_gateway_path

    self.__ag_interface = dbus.Interface(
      hfp.bus().get_object(
        hfp.HFPD_SERVICE_NAME,
        audio_gateway_path
      ),
      dbus_interface = hfp.HFPD_AUDIOGATEWAY_INTERFACE_NAME
    )

    self.__ag_properties = dbus.Interface(
      hfp.bus().get_object(
        hfp.HFPD_SERVICE_NAME,
        audio_gateway_path
      ),
      dbus_interface = hfp.DBUS_INTERFACE_PROPERTIES
    )

    self.__ag_interface.connect_to_signal('StateChanged',
      self.__gateway_state_changed)
    self.__ag_interface.connect_to_signal('CallStateChanged',
      self.__call_state_changed)
    self.__ag_interface.connect_to_signal('AudioStateChanged',
      self.__audio_state_changed)
    self.__ag_interface.connect_to_signal('AutoReconnectChanged',
      self.__auto_reconnect_changed)
    self.__ag_interface.connect_to_signal('Ring',
      self.__ring_notify)

  @ClassLogger.TraceAs.call()
  def connect(self):
    self.__ag_interface.Connect()

  @ClassLogger.TraceAs.call()
  def disconnect(self):
    self.__ag_interface.Disconnect()

  @ClassLogger.TraceAs.call()
  def start(self):
    self.connect()

  @ClassLogger.TraceAs.event()
  def answer(self):
    self.__ag_interface.Answer(
      reply_handler = lambda : None,
      error_handler = self.__failure
    )

  @ClassLogger.TraceAs.event()
  def hangup(self):
    self.__ag_interface.HangUp(
      reply_handler = lambda : None,
      error_handler = self.__failure
    )

  def enable_auto_reconnect(self):
    self.set_property('AutoReconnect', dbus.Boolean(True))

  def disable_auto_reconnect(self):
    self.set_property('AutoReconnect', dbus.Boolean(False))

  def auto_reconnect_enabled(self):
    bool(self.get_property('AutoReconnect'))

  def get_property(self, name):
    return self.__ag_properties.Set(
      self.__hfp.HFPD_AUDIOGATEWAY_INTERFACE_NAME,
      name
    )

  def set_property(self, name, value):
    return self.__ag_properties.Set(
      self.__hfp.HFPD_AUDIOGATEWAY_INTERFACE_NAME,
      name,
      value
    )

  @ClassLogger.TraceAs.event()
  def __gateway_state_changed(self, state, voluntary):
    state = int(state)
    if state == self.GatewayState.CONNECTED:
      self.enable_auto_reconnect()

  @ClassLogger.TraceAs.event()
  def __call_state_changed(self, state):
    pass

  @ClassLogger.TraceAs.event()
  def __audio_state_changed(self, state):
    pass

  @ClassLogger.TraceAs.event()
  def __auto_reconnect_changed(self, enabled):
    pass

  @ClassLogger.TraceAs.event()
  def __ring_notify(self, number, type, subaddr, satype, phonebook_entry):
    pass

  @ClassLogger.TraceAs.event()
  def __failure(self, reason):
    pass