#!/bin/bash

echo "Stopping pulseaudio..."
systemctl stop pulseaudio

echo "Adding pulse user, as system account..."
id -u pulse
if [ $? -ne 0 ]; then
  addgroup --system pulse
  adduser --system --ingroup pulse --home /var/run/pulse pulse
  addgroup --system pulse-access
  adduser pulse audio
else
  echo
  echo "WARNING:"
  echo "'pulse' user already exists, but may not be set up correctly"
  echo "for running pulseaudio in system mode (which is the mode you"
  echo "probably want to run it as on a Raspberry Pi). Consider removing"
  echo "the user and group 'pulse', and re-run this installation. This"
  echo "installation re-configures pulseaudio to run in system mode,"
  echo "which may not work correctly if the the user 'pulse' is not set"
  echo "up correctly."
  echo
fi

echo "Cleaning previous pulse runtime files..."
if [ -e /usr/local/var/run/pulse ]; then
  rm -rf /usr/local/var/run/pulse/*
  rm -rf /usr/local/var/run/pulse/.config
  rm -f /usr/local/var/run/pulse/.esd_auth
fi

echo "Fixing pulse directories..."
if [ -e /usr/local/var/lib ]; then
  chmod g-s /usr/local/var/lib
  chmod g+rx /usr/local/var/lib
fi

if [ -e /usr/local/var/run ]; then
  chmod g-s /usr/local/var/run
  chmod g+rx /usr/local/var/run
fi
