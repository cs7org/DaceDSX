# DaceDS4energy

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
