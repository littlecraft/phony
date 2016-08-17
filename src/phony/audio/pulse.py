import os
import dbus

from phony.base.log import ClassLogger

class PulseAudio(ClassLogger):
  PA_ROOT_INTERFACE = 'org.PulseAudio1'
  PA_SERVER_LOOKUP_PATH = '/org/pulseaudio/server_lookup1'
  PA_SERVER_LOOKUP_INTERFACE = 'org.PulseAudio.ServerLookup1'
  PA_CORE_PATH = '/org/pulseaudio/core1'
  PA_CORE_INTERFACE = 'org.PulseAudio.Core1'
  PA_DEVICE_INTERFACE = 'org.PulseAudio.Core1.Device'

  DBUS_PROPERTIES_INTERFACE = 'org.freedesktop.DBus.Properties'

  _server_address = None

  _bus = None
  _connection = None
  _core = None
  _core_properties = None
  _sink_properties_by_path = None
  _source_properties_by_path = None

  _microphone_source_hint = None
  _primary_audio_sink_hint = None

  _microphone_source_path = None
  _microphone_source_properties = None

  _primary_audio_sink_path = None
  _primary_audio_sink_properties = None

  _microphone_to_primary_loopback = None

  def __init__(self, bus_provider, server_address = None, microphone_source_hint = None, primary_audio_sink_hint = None):
    ClassLogger.__init__(self)

    self._bus = bus_provider.session_bus()
    self._server_address = server_address

    self._microphone_source_hint = microphone_source_hint
    self._primary_audio_sink_hint = primary_audio_sink_hint

  @ClassLogger.TraceAs.call()
  def start(self):
    self._connection = self._connect_to_server(self._server_address)
    self._core = self._connection.get_object(
      PulseAudio.PA_CORE_INTERFACE,
      PulseAudio.PA_CORE_PATH
    )
    self._core_properties = dbus.Interface(
      self._core,
      PulseAudio.DBUS_PROPERTIES_INTERFACE
    )

    self._collect_sinks()
    self._collect_sources()

    self._show_properties()

    self._micophone_source_path, self._microphone_source_properties = \
      self._find_microphone_source(self._microphone_source_hint)

    self.log().info('Microphone source: %s' %
      self._get_device_property(self._microphone_source_properties, 'Name'))

    self._primary_audio_sink_path, self._primary_audio_sink_properties = \
      self._find_primary_audio_sink(self._primary_audio_sink_hint)

    self.log().info('Primary sink: %s' %
      self._get_device_property(self._primary_audio_sink_properties, 'Name'))

    self._loopback_microphone_to_primary_audio_sink()

  @ClassLogger.TraceAs.call()
  def _loopback_microphone_to_primary_audio_sink(self):

    sink = str(self._get_device_property(self._primary_audio_sink_properties, 'Name'))
    source = str(self._get_device_property(self._microphone_source_properties, 'Name'))

    self._microphone_to_primary_loopback = \
      self._core.LoadModule(
        'module-loopback',
        {
          'sink': sink,
          'source': source,
          'latency_msec': 1
        }
      )

  def _find_microphone_source(self, hint = None):
    for path, properties in self._source_properties_by_path.iteritems():
      name = self._get_device_property(properties, 'Name')
      if PulseAudio._is_suitable_microphone_source(name):
        if not hint:
          return (path, properties)
        else:
          if hint in name:
            return (path, properties)

    raise Exception('No suitable microphone source found (hint="%s")' % hint)

  def _find_primary_audio_sink(self, hint = None):
    for path, properties in self._sink_properties_by_path.iteritems():
      name = self._get_device_property(properties, 'Name')
      if PulseAudio._is_suitable_primary_audio_sink(name):
        if not hint:
          return (path, properties)
        else:
          if hint in name:
            return (path, properties)

    raise Exception('No suitable primary sink found (hint="%s")' % hint)

  def _collect_sinks(self):
    self._sink_properties_by_path = {}

    sinks = self._get_core_property('Sinks')

    for path in sinks:
      sink = self._connection.get_object(object_path = path)

      self._sink_properties_by_path[path] = \
        dbus.Interface(sink, PulseAudio.DBUS_PROPERTIES_INTERFACE)

  def _collect_sources(self):
    self._source_properties_by_path = {}

    sources = self._get_core_property('Sources')

    for path in sources:
      source = self._connection.get_object(object_path = path)

      self._source_properties_by_path[path] = \
        dbus.Interface(source, PulseAudio.DBUS_PROPERTIES_INTERFACE)

  @ClassLogger.TraceAs.call()
  def _connect_to_server(self, server_address = None):
    if not server_address:
      server_address = self._get_server_address()

    self.log().debug('PulseAudio server: %s' % server_address)

    return dbus.connection.Connection(server_address)

  def _get_server_address(self):
    if 'PULSE_DBUS_SERVER' in os.environ:
      address = os.environ['PULSE_DBUS_SERVER']
    else:
      server = self._bus.get_object(
        PulseAudio.PA_ROOT_INTERFACE,
        PulseAudio.PA_SERVER_LOOKUP_PATH
      )

      address = server.Get(
        PulseAudio.PA_SERVER_LOOKUP_INTERFACE,
        'Address',
        PulseAudio.DBUS_PROPERTIES_INTERFACE
      )

    return address

  def _show_properties(self):
    self.log().debug('PulseAudio version %s' % self._get_core_property('Version'))

    for path, properties in self._sink_properties_by_path.iteritems():
      self.log().debug('Sink %s: %s' % (path, self._get_device_property(properties, 'Name')))

    for path, properties in self._source_properties_by_path.iteritems():
      self.log().debug('Source %s: %s' % (path, self._get_device_property(properties, 'Name')))

  def _get_core_property(self, prop):
    return self._core_properties.Get(PulseAudio.PA_CORE_INTERFACE, prop)

  def _set_core_property(self, prop, value):
    self._core_properties.Set(PulseAudio.PA_CORE_INTERFACE, prop, value)

  def _get_device_property(self, device, prop):
    return device.Get(PulseAudio.PA_DEVICE_INTERFACE, prop)

  def _set_device_property(self, device, prop, value):
    device.Set(PulseAudio.PA_DEVICE_INTERFACE, prop, value)

  @staticmethod
  def _is_suitable_microphone_source(source_name):
    return source_name.startswith('alsa_input') and \
      (source_name.endswith('analog-stereo') or \
        source_name.endswith('analog-mono'))

  @staticmethod
  def _is_suitable_primary_audio_sink(sink_name):
    return sink_name.startswith('alsa_output') and \
      (sink_name.endswith('analog-stereo') or \
        sink_name.endswith('analog-mono'))

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    pass