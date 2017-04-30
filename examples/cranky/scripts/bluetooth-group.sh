#!/bin/bash

echo "Adding user pi to group bluetooth"
id -u pi
if [ $? -eq 0 ]; then
  usermod -a -G bluetooth pi
else
  echo "User pi does not exist, skipping..."
fi

echo "Adding user pulse to group bluetooth"
id -u pulse
if [ $? -ne 0 ]; then
  useradd pulse
fi

usermod -a -G bluetooth pulse
