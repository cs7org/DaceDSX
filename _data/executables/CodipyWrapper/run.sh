#!/bin/bash
DIR="/home/mohamed/Desktop/DaceDS/DaceDS4energy-main/codipy"
echo $DIR
cd $DIR
gnome-terminal --tab -- bash -c "cd $DIR && python3 simulation_run.py --config config_seeding_strategy_update2.xml --scenario $1 --instance $2; exec bash"
