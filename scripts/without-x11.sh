#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

eval `dbus-launch --auto-syntax`
python $DIR/../src/main.py "$@"
