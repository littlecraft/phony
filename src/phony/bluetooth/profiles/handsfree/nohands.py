import dbus
import phony.base.log

from dbus.mainloop.glib import DBusGMainLoop
from phony.base.log import ClassLogger, Levels

class DbusPaths:
  DBUS_SERVICE_NAME = 'org.freedesktop.DBus'
  DBUS_INTERFACE_DBUS = 'org.freedesktop.DBus'
  DBUS_INTERFACE_PROPERTIES = 'org.freedesktop.DBus.Properties'
  DBUS_BUS_OBJECT = '/org/freedesktop/DBus'

  #
  # These are the service and interface names exposed to dbus
  # by the hfpd (nohands) daemon.  @see hfconsole.in in the
  # source tree of the nohands project as a reference.
  #
  HFPD_HANDSFREE_INTERFACE_NAME = 'net.sf.nohands.hfpd.HandsFree'
  HFPD_SOUNDIO_INTERFACE_NAME = 'net.sf.nohands.hfpd.SoundIo'
  HFPD_AUDIOGATEWAY_INTERFACE_NAME = 'net.sf.nohands.hfpd.AudioGateway'
  HFPD_SERVICE_NAME = 'net.sf.nohands.hfpd'
  HFPD_HANDSFREE_OBJECT = '/net/sf/nohands/hfpd'
  HFPD_SOUNDIO_OBJECT = '/net/sf/nohands/hfpd/soundio'

class NoHands(ClassLogger):
  # Only supports this version of hfpd:
  HFPD_EXACT_VERSION = 4

  __started = False

  __bus = None
  __dbus_interface = None
  __hfpd_interface = None
  __hfpd_properties = None

  __dbus_signal_handler = None

  __audio_gateways = {}

  __audio_gateway_attached_listeners = []
  __audio_gateway_detached_listeners = []

  def __init__(self, bus):
    ClassLogger.__init__(self)

    self.__bus = bus.session_bus()

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
          DbusPaths.DBUS_SERVICE_NAME,
          DbusPaths.DBUS_BUS_OBJECT
        ),
        dbus_interface = DbusPaths.DBUS_INTERFACE_DBUS
      )

    except dbus.exception.DBusException, (ex):
      self.__fatal('Could not connect to D-Bus:\n%s' % str(ex))

    try:
      self.__hfpd_interface = dbus.Interface(
        self.__bus.get_object(
          DbusPaths.HFPD_SERVICE_NAME,
          DbusPaths.HFPD_HANDSFREE_OBJECT
        ),
        dbus_interface = DbusPaths.HFPD_HANDSFREE_INTERFACE_NAME
      )

      self.__hfpd_properties = dbus.Interface(
        self.__bus.get_object(
          DbusPaths.HFPD_SERVICE_NAME,
          DbusPaths.HFPD_HANDSFREE_OBJECT
        ),
        dbus_interface = DbusPaths.DBUS_INTERFACE_PROPERTIES
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

    self.__dbus_interface.connect_to_signal("NameOwnerChanged", self.name_owner_changed)

    self.__hfpd_interface.connect_to_signal('SystemStateChanged', self.system_state_changed)
    self.__hfpd_interface.connect_to_signal('AudioGatewayAdded', self.audio_gateway_added)
    self.__hfpd_interface.connect_to_signal('AudioGatewayRemoved', self.audio_gateway_removed)
    self.__hfpd_interface.connect_to_signal('LogMessage', self.log_message)

    self.log().info('Connected to Hfp service')

    self.__hfpd_interface.Start()

    self.__started = True

  def started(self):
    return self.__started

  @ClassLogger.TraceAs.call()
  def stop(self):
    pass

  @ClassLogger.TraceAs.event(log_level = Levels.INFO)
  def attach(self, adapter, device_address):
    try:
      # HfpAudioGateway class is constructed via AudioGatewayAdded signal handler
      audio_gateway_path = self.__hfpd_interface.AddDevice(device_address, False)
    except Exception, ex:
      self.log().error('Could not attach device ' + str(device_address) + ' : ' + str(ex))

  def detach(self, adapter, device_address):
    pass

  def on_attached(self, listener):
    self.__audio_gateway_attached_listeners.append(listener)

  def on_detached(self, listener):
    self.__audio_gateway_detached_listeners.append(listener)

  @ClassLogger.TraceAs.event(log_level = Levels.INFO)
  def attach_to_audio_gateway(self, audio_gateway_path):
    if str(audio_gateway_path) not in self.__audio_gateways:
      ag = HfpAudioGateway(self, audio_gateway_path)
      ag.start()
      self.__audio_gateways[str(audio_gateway_path)] = ag

  def audio_gateway_started(self, audio_gateway_path):
    for listener in self.__audio_gateway_attached_listeners:
      listener(str(audio_gateway_path))

  @ClassLogger.TraceAs.event(log_level = Levels.INFO)
  def detach_from_audio_gateway(self, audio_gateway_path):
    audio_gateway_path = str(audio_gateway_path)
    if audio_gateway_path in self.__audio_gateways:
      del self.__audio_gateways[audio_gateway_path]

      for listener in self.__audio_gateway_detached_listeners:
        listener(audio_gateway_path)

  def get_property(self, name):
    return self.__hfpd_properties.Get(DbusPaths.HFPD_HANDSFREE_INTERFACE_NAME, name)

  def set_property(self, name, value):
    self.__hfpd_properties.Set(DbusPaths.HFPD_HANDSFREE_INTERFACE_NAME, name, value)

  def bus(self):
    return self.__bus

  @ClassLogger.TraceAs.event()
  def system_state_changed(self, state):
    pass

  @ClassLogger.TraceAs.event()
  def audio_gateway_added(self, audio_gateway_path):
    self.attach_to_audio_gateway(audio_gateway_path)

  @ClassLogger.TraceAs.event()
  def audio_gateway_removed(self, audio_gateway_path):
    self.detach_from_audio_gateway(audio_gateway_path)

  def log_message(self, level, msg):
    self.log().log(self.__normalize_log_level(level), 'HFPD: ' +  msg)

  @ClassLogger.TraceAs.event()
  def name_owner_changed(self, name, old_owner, new_owner):
    if name != DbusPaths.HFPD_SERVICE_NAME or new_owner != '':
      return

    self.log().debug('hfpd service disappeared, stopping');
    self.stop()

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

  @ClassLogger.TraceAs.event(log_level = Levels.ERROR)
  def __fatal(self, msg):
    raise Exception(msg)

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

    @classmethod
    def connected(cls, state):
      return state == cls.CONNECTED

    @classmethod
    def disconnected(cls, state):
      return state == cls.INVALID \
        or state == cls.DESTROYED \
        or state == cls.DISCONNECTED

  __ag_interface = None
  __ag_properties = None
  __path = None
  __features = []
  __soundio = None

  def __init__(self, hfp, audio_gateway_path):
    ClassLogger.__init__(self)

    self.__path = audio_gateway_path

    self.__ag_interface = dbus.Interface(
      hfp.bus().get_object(
        DbusPaths.HFPD_SERVICE_NAME,
        audio_gateway_path
      ),
      dbus_interface = DbusPaths.HFPD_AUDIOGATEWAY_INTERFACE_NAME
    )

    self.__ag_properties = dbus.Interface(
      hfp.bus().get_object(
        DbusPaths.HFPD_SERVICE_NAME,
        audio_gateway_path
      ),
      dbus_interface = DbusPaths.DBUS_INTERFACE_PROPERTIES
    )

    self.__ag_interface.connect_to_signal('StateChanged',
      self.__gateway_state_changed)
    self.__ag_interface.connect_to_signal('CallStateChanged',
      self.__call_state_changed)
    self.__ag_interface.connect_to_signal('AudioStateChanged',
      self.__audio_state_changed)
    self.__ag_interface.connect_to_signal('AutoReconnectChanged',
      self.__auto_reconnect_changed)
    self.__ag_interface.connect_to_signal('VoiceRecognitionActiveChanged',
      self.__voice_recognition_changed)
    self.__ag_interface.connect_to_signal('Ring',
      self.__ringing)

    self.__soundio = HfpSoundIo(hfp, self)

  @ClassLogger.TraceAs.call()
  def start(self):
    # Further state change occurs in __gateway_state_changed
    self.__ag_interface.Connect()

  @ClassLogger.TraceAs.call()
  def stop(self):
    # Further state change occurs in __gateway_state_changed
    self.__ag_interface.Disconnect()

  def path(self):
    return self.__path

  @ClassLogger.TraceAs.event(log_level = Levels.INFO)
  def answer(self):
    self.__ag_interface.Answer(
      reply_handler = lambda : None,
      error_handler = self.__failure
    )

  @ClassLogger.TraceAs.event(log_level = Levels.INFO)
  def hangup(self):
    self.__ag_interface.HangUp(
      reply_handler = lambda : None,
      error_handler = self.__failure
    )

  @ClassLogger.TraceAs.event(log_level = Levels.INFO)
  def voice_dial(self):
    if not self.has_feature('VoiceRecognition'):
      return self.__failure('Voice recognition is not supported by phone')

    self.__ag_interface.SetVoiceRecognition(dbus.Boolean(True))

  def get_property(self, name):
    return self.__ag_properties.Get(
      DbusPaths.HFPD_AUDIOGATEWAY_INTERFACE_NAME,
      name
    )

  def set_property(self, name, value):
    return self.__ag_properties.Set(
      DbusPaths.HFPD_AUDIOGATEWAY_INTERFACE_NAME,
      name,
      value
    )

  def has_feature(self, feature):
    return feature in self.__features

  def __refresh_features(self):
    self.__features = []

    try:
      self.__features = self.get_property('Features')
      for feature in self.__features:
        self.log().debug('Feature: ' + feature)
    except ex:
      self.__failure(str(ex))

  def __gatway_connected(self):
    self.__refresh_features()
    self.__enable_reconnect()
    self.__open_audio()

  def __gateway_disconnected(self):
    pass

  def __enable_reconnect(self):
    self.set_property('AutoReconnect', dbus.Boolean(True))

  def __open_audio(self):
    self.__ag_interface.OpenAudio()
    self.__soundio.start()

  @ClassLogger.TraceAs.event()
  def __gateway_state_changed(self, state, voluntary):
    state = int(state)
    if self.GatewayState.connected(state):
      self.__gatway_connected()
    elif self.GatewayState.disconnected(state):
      self.__gateway_disconnected()

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
  def __voice_recognition_changed(self, state):
    pass

  @ClassLogger.TraceAs.event(log_level = Levels.INFO)
  def __ringing(self, number, type, subaddr, satype, phonebook_entry):
    pass

  @ClassLogger.TraceAs.event(log_level = Levels.ERROR)
  def __failure(self, reason):
    pass

class HfpSoundIo(ClassLogger):

  class AudioState:
    INVALID = 0
    DISCONNECTED = 1
    CONNECTING = 2
    CONNECTED = 3

  __sound_io_interface = None
  __sound_io_properties = None
  __audio_gateway_path = None

  def __init__(self, hfp, audio_gateway):
    ClassLogger.__init__(self)

    self.__audio_gateway_path = audio_gateway.path()

    self.__sound_io_interface = dbus.Interface(
      hfp.bus().get_object(
        DbusPaths.HFPD_SERVICE_NAME,
        DbusPaths.HFPD_SOUNDIO_OBJECT
      ),
      dbus_interface = DbusPaths.HFPD_SOUNDIO_INTERFACE_NAME
    )

    self.__sound_io_properties = dbus.Interface(
      hfp.bus().get_object(
        DbusPaths.HFPD_SERVICE_NAME,
        DbusPaths.HFPD_SOUNDIO_OBJECT
      ),
      dbus_interface = DbusPaths.DBUS_INTERFACE_PROPERTIES
    )

    self.__sound_io_interface.connect_to_signal('StateChanged', self.__state_changed)
    self.__sound_io_interface.connect_to_signal('MuteChanged', self.__mute_changed)
    self.__sound_io_interface.connect_to_signal('SkewNotify', self.__skew_notify)

    self.__sound_io_interface.MinBufferFillHint = 320 * 2

  @ClassLogger.TraceAs.call()
  def start(self):
    try:
      self.__sound_io_interface.AudioGatewayStart(self.__audio_gateway_path, False)
    except ex:
      self.__failure(str(ex))

  @ClassLogger.TraceAs.event()
  def __state_changed(self, state):
    pass

  @ClassLogger.TraceAs.event()
  def __stream_aborted(self):
    pass

  @ClassLogger.TraceAs.event()
  def __mute_changed(self, state):
    pass

  @ClassLogger.TraceAs.event()
  def __skew_notify(self, skewtype, constructed):
    pass

  @ClassLogger.TraceAs.event(log_level = Levels.ERROR)
  def __failure(self, reason):
    pass
