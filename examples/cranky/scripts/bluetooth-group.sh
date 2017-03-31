#!/bin/bash

echo Adding user pi to group bluetooth
usermod -a -G bluetooth pi
echo Adding user pulse to group bluetooth
usermod -a -G bluetooth pulse
