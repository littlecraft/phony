# phony
The goal of this module is to provide a convenient python based bluetooth Handsfree Profile service which allows you to 'roll your own' hands free device.  Just Hook up a button or switch, a microphon and a speaker up to a raspberry pi, and now you have a hands free 'head set' to play with.

# Usage
0. Ensure that you have an HFP capable bluetooth dongle or adapter (e.g. a CSR8510 A10, or BCM20702A0).  If you are using a BCM20702A0, you may need to ensure that an updated firmware payload is being used.  [See this discussion](http://plugable.com/2014/06/23/plugable-usb-bluetooth-adapter-solving-hfphsp-profile-issues-on-linux)
1. Install bluez5.37, ofono1.17, pulseaudio8
2. Edit /etc/pulse/default.pa, ```load-module module-bluetooth-discover headset=ofono```
3. python src/main.py

# Roadmap
1. Raspberry pi GPIO hooks for ringer and hook
