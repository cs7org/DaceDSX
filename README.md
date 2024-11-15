# DaceDS4energy

This repository is a new version of DaceDS from Moritz Gütlein. 
DaceDS is a data-centric Distributed Simulation framework that focuses on data and loose couplings between components. 
It enables to combine various black-boxes in a plug-and-play manner. 
The connection of simulators, the integrating of data sources, the provision of data & interaction interfaces for external components, as well as the orchestration of simulation runs is covered. 
All communication is realized via a topic-based publish/subscribe paradigm on top of Apache Kafka.

In this repository we will further develop DaceDS to improve its initial state and to match the needs of the energy research community.
In the future we will add more wrappers for simulators and new features. 
In the following you will find a guide on how to install and run DaceDS with the implemented wrappers.
Further we provide a contribution guide and information on the licensing and publications.

# Installation guide
## What to install

* [JDK 11](https://jdk.java.net/archive/) 
  * set JAVA_Home
  * add %JAVA_HOME%\bin to your Path
* Install [Maven](https://maven.apache.org/download.cgi) and add it to your Path
* For Windows Users: Install [WSL](https://learn.microsoft.com/de-de/windows/wsl/install)
* Install [Docker](https://docs.docker.com/engine/install/)
* Setup [Confluent](https://docs.confluent.io/platform/current/platform-quickstart.html#qs-prereq) Platform with [Zookeeper](https://github.com/confluentinc/cp-all-in-one/blob/7.5.2-post/cp-all-in-one/docker-compose.yml)
* For Windows Users: If an error occurs during the installation of docker or confluent try:
  * dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
  * wsl --update



## What to do to run a Scenario in DaceDS:
1.	Make sure to compile the JavaBaseWrapper and SimService (just run “mvn install” in that folder)
2.	Make sure a config.properties is next to the SimService-0.1-jar-with-dependencies.jar and SendScenarioObject.jar
3.	Open Docker and run Kafka:
 * docker-compose up -d
 * docker-compose ps
4.	Run the SimService:
* (sudo) java -jar ./path_to/SimService-0.1-jar-with-dependencies.jar
5.	Run the SendScenarioObject with your scenario file as input
* (sudo) java -jar ./path_to/SendScenarioObject.jar ./path_to_scenario/scenario_file.json

## What to do to compile the SumoWrapper:
1.	Install sumo
* https://sumo.dlr.de/docs/Installing/
* https://sumo.dlr.de/docs/Installing/Linux_Build.html
2.	Install missing libraries
* (libserdes++)
* libavrocpp,
* librdkafka
* (libcppkafka)
* pugixml
3.	Compile CppBaseWrapper
* mkdir build
* cd build
* cmake ..
* make
4.	Compile SumoWrapper
* Adjust Makefile
* Run make
5. Install gnome-terminal
6. Make sure the paths in `_data\executables\SumoWrapper\run.sh` are correct before running a scenario

## What to do to run a PyPSA-scenario:

1. Install Python [(Download Link)](https://www.python.org/downloads/)
2. Install PyPSA [(Installation Guide)](https://pypsa-eur.readthedocs.io/en/latest/installation.html)
3. Install [confluent-kafka](https://pypi.org/project/confluent-kafka/)
4. Install [avro](https://pypi.org/project/avro/) (Maybe you also have to install [pytables](https://www.pytables.org/usersguide/installation.html))
5. Create a scenario file and place it under _data/scenarios
6. Run the scenario by following the *"What to do to run a scenario"* instructions

# Further information
## How to Contribute
You are welcome to contribute to DaceDS via bug reports and feature requests at any time.

## License
This work is licensed under the Apache License, Version 2.0. 
You can find further information in the [LICENSE](./LICENSE)-file or on this [website](http://www.apache.org/licenses/LICENSE-2.0).

## Publications

Main conceptual ideas can be found in the following publications:

- M. Gütlein and A. Djanatliev, "On-demand Simulation of Future Mobility Based on Apache Kafka," in Simulation and Modeling Methodologies, Technologies and Applications, ser. Lecture Notes in Networks and Systems, M. S. OBAIDAT, T. OREN, and F. D. RANGO, Eds. Cham: Springer International Publishing, 2022, pp. 18–41.
- M. Gütlein, R. German , and A. Djanatliev, "Hide Your Model! Layer Abstractions for Data-Driven Co-Simulations," in 2021 Winter Simulation Conference (WSC). IEEE, Dec. 2021, pp. 1–12.
- M. Gütlein, W. Baron, C. Renner, and A. Djanatliev, ``Performance Evaluation of HLA RTI Implementations," in 2020 IEEE/ACM 24th International Symposium on Distributed Simulation and Real Time Applications (DS-RT). IEEE, Sep. 2020, pp. 1–8.
- M. Gütlein and A. Djanatliev, "Modeling and Simulation as a Service using Apache Kafka:," in Proceedings of the 10th International Conference on Simulation and Modeling Methodologies, Technologies and Applications. SCITEPRESS - Science and Technology Publications, 2020, pp. 171–180.
- M. Gütlein and A. Djanatliev , "Coupled Traffic Simulation by Detached Translation Federates: An HLA-Based Approach," in 2019 Winter Simulation Conference (WSC). National Harbor, MD, USA: IEEE, Dec. 2019, pp. 1378–1389.
- M. Gütlein, R. German , and A. Djanatliev , "Towards a Hybrid Co-simulation Framework: HLA-Based Coupling of MATSim and SUMO," in 2018 IEEE/ACM 22nd International Symposium on Distributed Simulation and Real Time Applications (DS-RT).IEEE, 2018, pp. 1–9.
