#!/bin/bash
# $1: scenario id
# $2: simulator id

set -e
cd "$(dirname "$0")/../../../pandapowerWrapper"
exec python3 ./pandapowerWrapper.py "$1" "$2"
