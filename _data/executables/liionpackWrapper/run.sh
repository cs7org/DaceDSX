#!/bin/bash
# $1: scenario id
# $2: simulator id

set -e
cd "$(dirname "$0")/../../../liionpackWrapper"
exec python3 ./liionpackWrapper.py "$1" "$2"
