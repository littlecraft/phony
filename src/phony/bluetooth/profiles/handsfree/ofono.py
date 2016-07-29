import dbus
import dbus.service
import time
import glib

from phony.base.log import ClassLogger, ScopedLogger, Levels

class Ofono(ClassLogger):
  SERVICE_NAME = 'org.ofono'
  MANAGER_INTERFACE = 'org.ofono.Manager'
  HFP_INTERFACE = 'org.ofono.Handsfree'
  MODEM_INTERFACE = 'org.ofono.Modem'
  VOICE_CALL_MANAGER_INTERFACE = 'org.ofono.VoiceCallManager'

  __bus = None
  __manager = None

  __modem = None

  __adapter = None
  __device = None

  __found_hfp_audio_gateway_listener = None

  def __init__(self, bus):
    ClassLogger.__init__(self)

    self.__bus = bus.system_bus()

  @ClassLogger.TraceAs.call()
  def start(self):
    self.__manager = dbus.Interface(
      self.__bus.get_object(self.SERVICE_NAME, '/'),
      self.MANAGER_INTERFACE
    )

    self.__manager.connect_to_signal('ModemAdded', self.modem_added)
    self.__manager.connect_to_signal('ModemRemoved', self.modem_removed)

  @ClassLogger.TraceAs.call()
  def stop(self):
    pass

  @ClassLogger.TraceAs.call()
  def attach_audio_gateway(self, adapter, device, listener):
    self.__modem = None
    self.__found_hfp_audio_gateway_listener = None

    self.__adapter = adapter
    self.__device = device

    path, properties = self.__find_our_hfp_modem()

    # It's already available, so use it.
    if path and properties['Online']:
      self.log().debug('Found modem immediately!')
      self.__show_modem_properties(properties)
      listener(OfonoHandsFreeAudioGateway(path, self.__bus))
      return

    if path:
      # If one was found, but it is not yet online,
      # wait for it to go online.

      self.log().debug('Found modem, but it is offline, waiting for it to come online')

      self.__modem = dbus.Interface(
        self.__bus.get_object(self.SERVICE_NAME, path),
        self.MODEM_INTERFACE
      )

      self.__modem.connect_to_signal('PropertyChanged',
        self.wait_for_modem_to_go_online)
    else:
      # Otherwise, wait for the modem to be attached
      # to the adapter and device.

      self.log().debug('No modem found, waiting for one to appear')

    self.__found_hfp_audio_gateway_listener = listener

  @ClassLogger.TraceAs.event()
  def modem_added(self, path, properties):
    pass

  @ClassLogger.TraceAs.event()
  def modem_removed(self, path):
    pass

  def wait_for_modem_to_go_online(self, name, value):
    if self.__modem:
      if name == 'Online' and value:
        self.log().debug('Modem is online, notifying...')
        ag = OfonoHandsFreeAudioGateway(self.__modem.object_path, self.__bus)
        self.__found_hfp_audio_gateway_listener(ag)

        self.__modem = None
        self.__adapter = None
        self.__device = None


  def __find_our_hfp_modem(self):
    found_path = None
    found_properties = None

    modems = self.__manager.GetModems()

    # TODO: Verify that the modem is attached to _both_
    # the adapter and remote device.  This is necessary
    # in cases where the host has more than one BT adapter.

    for path, properties in modems:
      if self.__is_our_hfp_modem(path, properties):
        found_path = path
        found_properties = properties
        break

    return (found_path, found_properties)

  def __is_our_hfp_modem(self, path, properties):
    path = path.replace('_', ':')
    path = path.upper()
    return path.endswith(self.__device.address()) \
      and properties['Type'] == 'hfp'

  def __show_modem_properties(self, properties):
    self.log().info('Device Name: ' + properties['Name'])
    self.log().info('Device Profile Type: ' + properties['Type'])
    self.log().info('Device Online: %s' % properties['Online'])

    ifaces = ''
    for iface in properties['Interfaces']:
      ifaces += iface + ' '
    self.log().info('Device Interfaces: %s' % ifaces)

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    pass

class OfonoHandsFreeAudioGateway(ClassLogger):
  __path = None
  __hfp = None
  __voice_call_manager = None

  def __init__(self, path, bus):
    ClassLogger.__init__(self)

    self.__bus = bus
    self.__path = path

    self.__hfp = dbus.Interface(
      self.__bus.get_object(Ofono.SERVICE_NAME, self.__path),
      Ofono.HFP_INTERFACE
    )

    self.__voice_call_manager = dbus.Interface(
      self.__bus.get_object(Ofono.SERVICE_NAME, self.__path),
      Ofono.VOICE_CALL_MANAGER_INTERFACE
    )

  def provides_voice_recognition(self):
    return 'voice-recognition' in self.__hfp.GetProperties()['Features']

  @ClassLogger.TraceAs.event()
  def begin_voice_dial(self):
    if not self.provides_voice_recognition():
      raise Exception('Device does not support voice recognition')

    self.__hfp.SetProperty('VoiceRecognition', True)

  @ClassLogger.TraceAs.event()
  def cancel_voice_dial(self):
    if not self.provides_voice_recognition():
      raise Exception('Device does not support voice recognition')

    self.__hfp.SetProperty('VoiceRecognition', False)

  @ClassLogger.TraceAs.event()
  def dial(self, number):
    dial_path = self.__voice_call_manager.Dial(number, 'default')

  def __show_hands_free_properties(self):
    properties = self.__hfp.GetProperties()

    features = ''
    for feature in properties['Features']:
      features += feature + ' '
    self.log().info('Device HFP Features: %s' % features)