# phony
A Python based bluetooth hands free telephone device, still in development.  Provides a bluetooth hands free profile service which turns your device (or linux machine) into a bluetooth hands free device, capable of making voice-dialed phone calls, with audio is routed through your devices sound card.

# Usage
1. Pull & build [handsfree, aka hfpd](https://github.com/heinervdm/nohands)
1. Start hfpd
1. ```git clone https://github.com/littlecraft/phony.git```
1. Ensure that all packages in phony/packages.txt are installed
1. Do this

    ```bash
    $ cd phony
    $ source ./env.sh
    $ python src/main.py --name='MyBTHandsFreeDevice' [--interface=<bluetooth-mac-addr>] [--pin=<legacy-paring-pin>] 
    ```
