# DaceDS4energy

## What to install

* [JDK 11](https://jdk.java.net/archive/) 
  * set JAVA_Home
  * add %JAVA_HOME%\bin ti Path
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

5.	Run the SimService:
* (sudo) java -jar ./path_to/SimService-0.1-jar-with-dependencies.jar
6.	Run the SendScenarioObject with your scenario file as input
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
5.	Make sure the paths in `_data\executables\SumoWrapper\run.sh` are correct before running a scenario
