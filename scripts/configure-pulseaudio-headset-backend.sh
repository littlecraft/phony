#!/bin/bash

if [ -e /usr/local/etc/pulse/default.pa ]
then
  echo "Configuring /usr/local/bin/pulseaudio to use ofono as headset backend"
  sed -i 's/module-bluetooth-discover$/module-bluetooth-discover headset=ofono/' /usr/local/etc/pulse/default.pa
fi

if [ -e /etc/pulse/default.pa ]
then
  echo "Configuring /usr/bin/pulseaudio to use ofono as headset backend"
  sed -i 's/module-bluetooth-discover$/module-bluetooth-discover headset=ofono/' /etc/pulse/default.pa
fi
