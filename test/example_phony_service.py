import gobject
import phony.headset
import phony.base.ipc
import phony.base.log
import phony.audio.alsa
import phony.bluetooth.adapters
import phony.bluetooth.profiles.handsfree

class ExampleHeadsetService:
  _hs = None
  _call_in_progress = False

  def device_connected(self):
    print 'Device connected!'

  def incoming_call(self, call):
    print 'Incoming call: %s' % call
    if self._call_in_progress:
      self._hs.deflect_call_to_voicemail()

  def call_began(self, call):
    print 'Call began: %s' % call
    self._call_in_progress = True

  def call_ended(self, call):
    print 'Call ended: %s' % call
    self._call_in_progress = False

  def run(self):
    """
    Starts phony service which manages device pairing and setting
    up of hands-free profile services.  This function never returns.
    """
    bus = phony.base.ipc.BusProvider()

    # Find the first audio card that provides
    # audio input and output mixers.
    audio_card_index = -1

    with phony.bluetooth.adapters.Bluez5(bus) as adapter, \
         phony.bluetooth.profiles.handsfree.Ofono(bus) as hfp, \
         phony.audio.alsa.Alsa(card_index=audio_card_index) as audio, \
         phony.headset.HandsFreeHeadset(bus, adapter, hfp, audio) as hs:

      # Register to receive some bluetooth events
      hs.on_device_connected(self.device_connected)
      hs.on_incoming_call(self.incoming_call)
      hs.on_call_began(self.call_began)
      hs.on_call_ended(self.call_ended)

      hs.start('MyBluetoothHeadset', pincode='1234')
      hs.enable_pairability(timeout=30)

      self._hs = hs

      # Wait forever
      gobject.MainLoop().run()

  #
  # Call these from your event handlers
  #

  def voice_dial(self):
    self._hs.initiate_call()

  def dial_number(self, phone_number):
    self._hs.dial(phone_number)

  def answer(self):
    self._hs.answer_call()

  def hangup(self):
    self._hs.hangup()

if __name__ == '__main__':
  # Enable debug logging to the console
  phony.base.log.send_to_stdout()

  #
  # Start the HFP service class, and never return.
  #
  # You can now pair your phone, and phony will setup
  # the necessary HFP profile services.
  #
  # To actually voice dial, dial a number or hangup a call,
  # you must call the voice_dial, dial_number, answer, or
  # hangup methods above from some kind of an asynchronous
  # event handler, like in response to some input on stdin,
  # or a button click, or a GPIO event, or maybe a command
  # sent over SPI or i2c.
  #
  service = ExampleHeadsetService()
  service.run()
