#!/bin/bash

# $1: scenario id
# $2: simulator id

set -e
cd "$(dirname "$0")/../../../SumoWrapper"
export LD_LIBRARY_PATH="../CppBaseWrapper/build"
exec ./SumoWrapper "$1" "$2"
