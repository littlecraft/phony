#!/bin/bash

echo "Adding pulse user"
id -u pulse
if [ $? -ne 0 ]; then
  useradd pulse
fi

echo "Fixing pulse directories..."
if [-e /usr/local/var/lib]; then
  chmod g-s /usr/local/var/lib
  chmod g+rx /usr/local/var/lib
fi

if [ -e /usr/local/var/run ]; then
  chmod g-s /usr/local/var/run
  chmod g+rx /usr/local/var/run
fi
