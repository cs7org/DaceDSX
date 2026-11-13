#!/bin/bash
# $1: scenario id
# $2: simulator id

set -e
cd "$(dirname "$0")/../../../../Translators"
exec python3 ./energy_ontology_transformer.py "$1" "$2"
