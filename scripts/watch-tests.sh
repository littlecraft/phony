#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

source ./env.sh
pushd .
cd $DIR/..
ptw
popd
