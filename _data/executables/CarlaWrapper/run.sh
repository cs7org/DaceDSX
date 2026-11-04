#!/bin/bash
# $1: scenario id
# $2: simulator id

set -e
cd "$(dirname "$0")/../../../CarlaWrapper"
exec python3 ./CarlaWrapper.py "$1" "$2"
