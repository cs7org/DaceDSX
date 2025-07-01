#!/bin/bash


docker compose up -d 

cd SimService

gnome-terminal -- bash -c "java -jar ./target/SimService-0.1-jar-with-dependencies.jar; exec bash"

sleep 15

gnome-terminal -- bash -c "java -jar ./target/SendScenarioObject.jar '$1'; exec bash"
