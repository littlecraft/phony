# phony
A Python based bluetooth hands free telephone device, still in development.  Provides a bluetooth hands free profile service which turns your device (or linux machine) into a bluetooth hands free device, capable of making voice-dialed phone calls, with audio that is routed through your device's sound card.

# Usage
1. Install and run hfpd
    1. ```git clone https://github.com/heinervdm/nohands.git```
    1. ```$ cd nohands && ./configure && make```
    1. ```$ cd hfpd```
    1. ```$ ./hfpd -f```
1. Let that run, and install dependencies and run this project
    1. ```git clone https://github.com/littlecraft/phony.git```
    1. Ensure that all packages in phony/packages.txt are installed
    1. ```$ pip install virtualenv```
    1. ```$ cd phony```
    1. ```$ source ./env.sh```
    1. ``` $ python src/main.py --name='MyBTHandsFreeDevice' [--interface=<bluetooth-mac-addr>] [--pin=<legacy-paring-pin>]```

# Roadmap
1. Establish audio & voice dialing with device (still in development)
1. Event callback mechanism for ringing, answer, hangup, and initiating voice dialing
1. Improve device auto-reconnect
