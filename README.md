# phony
Phony is a python module that provides a convenient bluetooth hands-free profile (HFP) interface and allows you to easily create your very own linux-based hands free service or device.

Phony collects and abstracts much of the tedium and mystery associated with working with the linux bluetooth, telephony, and audio stack.  And what's more, it is designed to be deeply embedded, making it great for environments with limited or no HMI.

# Prerequisites

1. Linux Kernel 4.x (Tested on 4.4.x)
1. Bluez5 (Tested with v5.23)
1. Ofono (Testes with v1.17)
1. Pulseaudio 7

_Note: The particular versions of these dependencies may need to be built from source.  See Appendix B_


# Installation

```
$ sudo apt-get install python-dev python-setuptools python-gobject python-dbus rfkill
$ git clone https://github.com/littlecraft/phony.git
$ cd phony
$ python setup.py install
```

_Note: Installing phony will attempt to automatically configure Pulseaudio to use ofono as the bluetooth headset backend. [See the HFP section here for more info](https://freedesktop.org/wiki/Software/PulseAudio/Documentation/User/Bluetooth/)._

# Usage

### A complete example

For a complete example, see [examples/cranky](https://github.com/littlecraft/phony/tree/master/examples/cranky) which uses phony and a Raspberry Pi to turn a 1900's era hand crank telephone into a voice dialing bluetooth 'headset'.  Just like SparkFun's [Port-O-Rotary](https://www.sparkfun.com/products/retired/287), but even more retro!

### Example of how to start the headset service, providing voice and numeric dialing

```python
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

    # -1 find the first audio card that provides
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
```


# Appendix A: Hardware

## Audio

Phony requires an audio adapter that has an audio input and an output.  If you intend to use phony on a device like a Raspberry Pi, you will need an external audio adapter, like this one:

* [USB Audio Adapter](https://www.amazon.com/Sabrent-External-Adapter-Windows-AU-MMSA/dp/B00IRVQ0F8)


## Bluetooth

Ensure that you have an HFP capable bluetooth dongle or adapter (e.g. a CSR8510 A10, or BCM20702A0 work well).

Tested bluetooth adapters:

| Adapter      | HFP Works? |
| ------------ | -------- |
| Panda Bluetooth 4.0 (USBCSR8510 A10) | Yes |
| Plugable USB Bluetooth 4.0 (BCM20702A0)<sup>1</sup> | Yes |
| Raspberry Pi 3 integrated Bluetooth (BCM43438)<sup>2</sup> | No |


_1 If you are using a BCM20702A0, you may need to ensure that an updated firmware payload is being used.  [See this discussion](http://plugable.com/2014/06/23/plugable-usb-bluetooth-adapter-solving-hfphsp-profile-issues-on-linux)_

_2 The integrated bluetooth chip onboard the Raspberry Pi 3 does not appear to work correctly with ofono's HFP implementation.  A separate USB bluetooth adapter is necessary._

# Appendix B: Building & Installing Prerequisites

## Building Bluez5

```
$ sudo apt-get install autoconf libtool intltool libdbus-1-dev libglib2.0-dev libudev-dev libical-dev libreadline-dev
$ git clone https://git.kernel.org/pub/scm/bluetooth/bluez.git
$ cd bluez
$ git checkout tags/5.23
$ ./bootstrap
$ ./configure
$ make -j4
$ sudo make install
```

## Building Ofono

```
$ sudo apt-get install autoconf libtool intltool libdbus-1-dev glib2.0 mobile-broadband-provider-info
$ git clone https://git.kernel.org/pub/scm/network/ofono/ofono.git
$ cd ofono
$ git checkout tags/1.17
$ ./bootstrap.sh
$ ./configure
$ make -j4
$ sudo make install
```

## Building Pulseaudio 7

```
$ sudo apt-get install autoconf libtool intltool libdbus-1-dev libsndfile1-dev libcap-dev libsystemd-daemon0 libspeex-dev libspeexdsp-dev libudev-dev libsbc-dev libbluetooth-dev libasound2-dev libjson-c-dev
$ git clone http://anongit.freedesktop.org/git/pulseaudio/pulseaudio.git
$ cd pulseaudio
$ git checkout tags/v7.0
$ ./bootstrap
$ ./configure
$ make -j4
$ sudo make install
```
