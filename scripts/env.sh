#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

#sudo pip install virtualenv

#PACKAGE_DIR=./.pip_packages
#VIRTUAL_BIN=$PACKAGE_DIR/bin

#virtualenv --system-site-packages $PACKAGE_DIR
#. $VIRTUAL_BIN/activate

#pip install pytest
#pip install pytest-watch
#pip install fysom

export PYTHONPATH=$PYTHONPATH:$DIR/../src
export PYTHONPATH=$PYTHONPATH:$DIR/../ext/fysom/main/python
#export PATH=$PATH:$VIRTUAL_BIN
