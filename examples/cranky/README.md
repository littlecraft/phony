# Overview
Cranky is an application using phony on a Raspberry Pi, creating an embedded, linux-based hands free bluetooth device from a 1900's era hand-crank telephone.

A custom [pi-hat](https://github.com/littlecraft/phony/tree/master/examples/cranky/hardware) is used to drive the ringer bells, and receive hardware events from the hook switch and magneto of the old telephone.  Much of the hardware design is borrowed from SparkFun's [Port-O-Rotary](https://www.sparkfun.com/products/retired/287), and adjusted to work with a much older generation of telephone.

In addition to that, the project uses the following off-the-shelf hardware (which is likely replaceable by other devices):

* [USB Audio Adapter](https://www.amazon.com/Sabrent-External-Adapter-Windows-AU-MMSA/dp/B00IRVQ0F8)
* [USB Bluetooth Adapter](https://www.amazon.com/Panda-Bluetooth-4-0-Nano-Adapter/dp/B00BCU4TZE)

But aside from its obviously impracticality, cranky can be used as a model for how you can turn a raspberry pi into your very own hands free device using phony, complete with an HMI using the raspberry pi's GPIO.

# Warning
By default cranky is installed as a background (systemd) service, and in order to make everything work, during installation, pulseaudio is configured to run as a background service as well.  This is a non-standard configuration, but for embedded systems, it is usually the way to go.  However, if you attempt to run the installation on your regular machine, you will likely discover that your audio no longer works as it had.

# Pre-requisits

Follow the installation and Appendix B pre-requisite instructions in the [README of the phony repo](https://github.com/littlecraft/phony)

# Installation

```
$ sudo apt-get install dbus-x11
$ sudo pip install -r requirements.txt
$ sudo python setup.py install
```

# Configure
Take a look at /etc/cranky/cranky.conf for configuration points.
```
[daemon]
#log_level=DEFAULT

[bluetooth]
#name=My Headset Gizmo
#interface=hci0
#pin=1234
#visibility_timeout=0

[audio]
#audio_card_index=-1
#mic_playback_volume=50
#mic_capture_volume=80
```

# Start cranky as a service
```
$ sudo systemctl start cranky
```

# Watch what happens
```
$ sudo journalctl -u cranky.service -f
Apr 29 02:25:49 raspberrypi cranky[2120]: 2017-04-29 02:25:49.994 phony.examples.cranky.main.ApplicationMain                   DEBUG    -> main_loop
Apr 29 02:28:21 raspberrypi cranky[2120]: 2017-04-29 02:28:21.731 phony.bluetooth.adapters.bluez5.Bluez5                       DEBUG    ** Bluez5.properties_changed(org.bluez.Device1, dbus.Dictionary({dbus...)
Apr 29 02:28:21 raspberrypi cranky[2120]: 2017-04-29 02:28:21.732 phony.bluetooth.adapters.bluez5.Bluez5                       INFO     Device: /org/bluez/hci0/dev_<YourDevicesMac> Connected
Apr 29 02:28:21 raspberrypi cranky[2120]: 2017-04-29 02:28:21.745 phony.headset.HandsFreeHeadset                               INFO     ** HandsFreeHeadset._device_connected(<YourDevicesMac> <YourDeviceName>)
Apr 29 02:28:21 raspberrypi cranky[2120]: 2017-04-29 02:28:21.754 phony.bluetooth.profiles.handsfree.ofono.Ofono               DEBUG    -> Ofono.attach_audio_gateway(<YourDevicesMac> raspberrypi #1, <YourDevicesMac>:...)
Apr 29 02:28:21 raspberrypi cranky[2120]: 2017-04-29 02:28:21.755 phony.bluetooth.profiles.handsfree.ofono.Ofono               DEBUG    <- Ofono.attach_audio_gateway(<YourDevicesMac> raspberrypi #1, <YourDevicesMac>:...)
Apr 29 02:28:22 raspberrypi cranky[2120]: 2017-04-29 02:28:22.442 phony.bluetooth.adapters.bluez5.PermissibleAgent             DEBUG    RequestConfirmation (/org/bluez/hci0/dev_<YourDevicesMac>, 552983)
Apr 29 02:28:22 raspberrypi cranky[2120]: 2017-04-29 02:28:22.763 phony.bluetooth.profiles.handsfree.ofono.Ofono               DEBUG    -> Ofono._poll_for_child_hfp_modem(<YourDevicesMac> raspberrypi #1, <YourDevicesMac>:...)
Apr 29 02:28:22 raspberrypi cranky[2120]: 2017-04-29 02:28:22.774 phony.bluetooth.profiles.handsfree.ofono.Ofono               DEBUG    <- Ofono._poll_for_child_hfp_modem(<YourDevicesMac> raspberrypi #1, <YourDevicesMac>:...)
Apr 29 02:28:23 raspberrypi cranky[2120]: 2017-04-29 02:28:23.764 phony.bluetooth.profiles.handsfree.ofono.Ofono               DEBUG    -> Ofono._poll_for_child_hfp_modem(<YourDevicesMac> raspberrypi #1, <YourDevicesMac>:...)
Apr 29 02:28:23 raspberrypi cranky[2120]: 2017-04-29 02:28:23.776 phony.bluetooth.profiles.handsfree.ofono.Ofono               DEBUG    <- Ofono._poll_for_child_hfp_modem(<YourDevicesMac> raspberrypi #1, <YourDevicesMac>:...)
Apr 29 02:28:24 raspberrypi cranky[2120]: 2017-04-29 02:28:24.765 phony.bluetooth.profiles.handsfree.ofono.Ofono               DEBUG    -> Ofono._poll_for_child_hfp_modem(<YourDevicesMac> raspberrypi #1, <YourDevicesMac>:...)
Apr 29 02:28:24 raspberrypi cranky[2120]: 2017-04-29 02:28:24.776 phony.bluetooth.profiles.handsfree.ofono.Ofono               DEBUG    <- Ofono._poll_for_child_hfp_modem(<YourDevicesMac> raspberrypi #1, <YourDevicesMac>:...)
Apr 29 02:28:25 raspberrypi cranky[2120]: 2017-04-29 02:28:25.767 phony.bluetooth.profiles.handsfree.ofono.Ofono               DEBUG    -> Ofono._poll_for_child_hfp_modem(<YourDevicesMac> raspberrypi #1, <YourDevicesMac>:...)
Apr 29 02:28:25 raspberrypi cranky[2120]: 2017-04-29 02:28:25.778 phony.bluetooth.profiles.handsfree.ofono.Ofono               DEBUG    <- Ofono._poll_for_child_hfp_modem(<YourDevicesMac> raspberrypi #1, <YourDevicesMac>:...)
Apr 29 02:28:26 raspberrypi cranky[2120]: 2017-04-29 02:28:26.321 phony.bluetooth.adapters.bluez5.PermissibleAgent             DEBUG    Authorize (/org/bluez/hci0/dev_<YourDevicesMac>, 0000111e-0000-1000-8000-00805f9b34fb)
Apr 29 02:28:26 raspberrypi cranky[2120]: 2017-04-29 02:28:26.769 phony.bluetooth.profiles.handsfree.ofono.Ofono               DEBUG    -> Ofono._poll_for_child_hfp_modem(<YourDevicesMac> raspberrypi #1, <YourDevicesMac>:...)
Apr 29 02:28:26 raspberrypi cranky[2120]: 2017-04-29 02:28:26.824 phony.bluetooth.profiles.handsfree.ofono.OfonoHfpAg          INFO     Device HFP Features: three-way-calling echo-canceling-and-noise-reduction voice-recognition release-all-held create-multiparty hf-indicators
Apr 29 02:28:26 raspberrypi cranky[2120]: 2017-04-29 02:28:26.828 phony.headset.HandsFreeHeadset                               INFO     ** HandsFreeHeadset._audio_gateway_attached(Path: /hfp/org/bluez/hci0/dev_<YourDevicesMac>...)
Apr 29 02:28:26 raspberrypi cranky[2120]: 2017-04-29 02:28:26.831 phony.examples.cranky.hmi.HandCrankTelephoneControls         DEBUG    ** HandCrankTelephoneControls._device_connected()
```

# Interactive REPL

```
$ sudo crankyctl
Welcome to cranky shell.  Type help or ? for list of commands.

(phony) help

Documented commands (type help <topic>):
========================================
help

Undocumented commands:
======================
answer  mic_volume  short_ring                  speaker_volume  stop_ringing
dial    mute        simulate_hand_crank_turned  start_ringing   unmute      
exit    quit        simulate_off_hook           state           voice       
hangup  reset       simulate_on_hook            status        

(phony) status
Device:   <YourDeviceMac> <YourDeviceName>
AudioGateway:   Path: /hfp/org/bluez/hci0/dev_<YourDeviceMac>
Features: three-way-calling echo-canceling-and-noise-reduction voice-recognition release-all-held create-multiparty hf-indicators 
Adapter:    <YourBluetoothDeviceMac> raspberrypi #1
AudioCard:    hw:1
(phony) simulate_off_hook
```
