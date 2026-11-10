#!/bin/bash
# $1: scenario id
# $2: simulator id

set -e
cd "$(dirname "$0")/../../../pvlibWrapper"
exec python3 ./pvlibWrapper.py "$1" "$2"
