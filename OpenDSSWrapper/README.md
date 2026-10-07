# OpenDSSWrapper

Integration of OpenDSS into DaceDSX, mirroring PyPSAWrapper.

## Files

| File | Purpose |
|------|---------|
| OpenDSSWrapper.py | DaceDSX glue (Kafka, TimeSync, main loop) |
| OpenDSSApi.py | OpenDSS logic (compile .dss, solve power flow) |
| run.sh | Launcher: accepts scenarioID + instanceID |
| config.properties | Broker / schema registry config |
| example/IEEE4Bus.dss | IEEE 4-bus test feeder |
| example/scenario.json | Reference scenario |

## Install

    pip install OpenDSSDirect.py confluent-kafka avro pandas

## Run

    ./run.sh <scenarioID> <instanceID>

## Workflow

1. Scenario with type OpenDSSWrapper is placed via SendScenarioObject.jar.
2. SimService executes _data/executables/OpenDSSWrapper/run.sh <sid> <iid>.
3. Wrapper reads scenario, joins TimeSync, compiles circuit, solves per step.
4. Bus voltages published on provision.simulation.<sid>.energy.<iid>.<bus>.

Reuses KafkaConsumer, KafkaProducer, TimeSync from PythonBaseWrapper.
