#!/bin/bash

DIR="/home/mohamed/Desktop/DaceDS"
OPPDIR="DaceDS4energy-main/OppWrapper/Wrapper"
cd "$DIR" || { echo "❌ Failed to cd into $DIR"; exit 1; }

echo "OMNeT++ dir: ${OMNETPP_DIR}"

ARGS="--KafkaBaseScenario.kmanager.mountainScenarioID=$1 --KafkaBaseScenario.kmanager.mountainSimulatorID=$2"

echo "$DIR/omnetpp-5.6.1-src-linux/omnetpp-5.6.1/bin/opp_run -m -u Qtenv -n $DIR/$OPPDIR/simulations:$DIR/veins-veins-5.1/src/veins --image-path=../../images -l veins -l Wrapper $ARGS"

gnome-terminal -- bash -c "$DIR/omnetpp-5.6.1-src-linux/omnetpp-5.6.1/bin/opp_run -m -u Qtenv \
  -n $DIR/$OPPDIR/simulations:$DIR/veins-veins-5.1/src/veins \
  --image-path=../../images \
  -l $DIR/veins-veins-5.1/out/gcc-release/src/veins \
  -l $DIR/$OPPDIR/src/libWrapper.so \
  $DIR/$OPPDIR/simulations/omnetpp.ini \
  --KafkaBaseScenario.kmanager.mountainScenarioID=$1 \
  --KafkaBaseScenario.kmanager.mountainSimulatorID=$2; exec bash"

