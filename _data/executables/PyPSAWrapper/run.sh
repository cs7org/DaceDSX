#!/bin/bash
# $1: scenario id
# $2: simulator id

set -e
cd "$(dirname "$0")/../../../PyPSAWrapper"
exec python3 ./PyPSAWrapper.py "$1" "$2"
