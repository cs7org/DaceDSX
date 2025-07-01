#!/bin/bash

gnome-terminal -- bash -c "java -jar ../Projectors/V2XProjector/target/V2XProjector.jar $1 $2; exec bash"
