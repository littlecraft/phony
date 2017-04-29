# Overview
Cranky is an example application for the raspberry pi, based on the phony module.  When accompanied by [custom supporting hardware](https://github.com/littlecraft/phony/tree/master/examples/cranky/hardware), as well as an external USB audio device, and Bluetooth adapter, this application is used to create a functional hands-free device out of a 1900's era hand-crank telephone.  Aside from its precise, and obviously impractical application, cranky can be used as a model for how you can turn a raspberry pi into your own hands free device, complete with an HMI using the raspberry pi's GPIO.

A custom pi-hat, [here](https://github.com/littlecraft/phony/tree/master/examples/cranky/hardware) is used to drive the ringer bells, and receieve hardware events from the hook switch and magneto of the old telephone.  In addition to this, the example project uses the following off-the-shelf hardware (which is likely replacible by other devices):

* [USB Audio Adapter](https://www.amazon.com/Sabrent-External-Adapter-Windows-AU-MMSA/dp/B00IRVQ0F8)
* [USB Bluetooth Adapter](https://www.amazon.com/Panda-Bluetooth-4-0-Nano-Adapter/dp/B00BCU4TZE)


# Pre-requisits

Follow the installation and Appendix B pre-requisite instructions in the [README within the phony repo](https://github.com/littlecraft/phony)

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
$ sudo cranky-client
```
