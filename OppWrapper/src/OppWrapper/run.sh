
#!/bin/bash
#../../bin/opp_run -r 0 -m -u Cmdenv -l tictoc omnetpp.ini --**.scenarioIDint=$1
BASEDIR="../OppWrapper/Wrapper/src/OppWrapper"

cd $BASEDIR

ARGS=' --KafkaBaseScenario.kmanager.mountainScenarioID=\"$1\" --KafkaBaseScenario.kmanager.mountainSimulatorID="'$2'"'
echo "../../../../bin/opp_run -m -u Qtenv -n .:../../simulations --image-path=../../images -l ../veins omnetpp.ini $ARGS"
../../../../bin/opp_run -m -u Qtenv -n ../../simulations:../../../../../veins-veins-5.1/src/veins:../ --image-path=../../images -l/home/mohamed/Desktop/DaceDS/veins-veins-5.1/out/gcc-release/src/veins -l//home/mohamed/Desktop/DaceDS/DaceDS4energy-main/OppWrapper/Wrapper/out/gcc-release/src/Wrapper ../../simulations/omnetpp.ini --KafkaBaseScenario.kmanager.mountainScenarioID=\"$1\" --KafkaBaseScenario.kmanager.mountainSimulatorID=\"$2\"

