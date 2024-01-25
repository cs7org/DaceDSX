# DaceDS4energy

## What to install

* The simulation service is implemented for Linux operating systems, if you want to use it on Windows install [WSL](https://learn.microsoft.com/de-de/windows/wsl/install) and run all the commands in the WSL (open the cmd and write bash to activate WSL)
* [JDK 11](https://jdk.java.net/archive/) 
  * set JAVA_Home
  * add %JAVA_HOME%\bin to your Path
* Install [Maven](https://maven.apache.org/download.cgi) and add it to your Path
* Install [Docker Desktop](https://docs.docker.com/engine/install/)
  * For Windows: Go to settings -> General and enable "Use the WSL 2 based engine"
  * For Linux: Go to settings -> General and enable "enable 'docker-compose' CLI alias" 
* Do step 1 of the [Setup Confluent Platform](https://docs.confluent.io/platform/current/platform-quickstart.html#qs-prereq)  using the [Zookeeper-compose file](https://github.com/confluentinc/cp-all-in-one/blob/7.5.2-post/cp-all-in-one/docker-compose.yml) instead of the wget command
* For Windows Users: If an error occurs during the installation of docker or confluent try:
  * dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
  * wsl --update


## How to compile DaceDS
1. Download or check-out this repo
2. Compile the JavaBaseWrapper and SimService (just run “mvn install” in that folder)
3. Compile (if necessary) the Wrapper-folder, e.g. as shown below for SumoWrapper


## What to do to run a Scenario in DaceDS:
1.	Make sure a config.properties is next to the SimService-0.1-jar-with-dependencies.jar and SendScenarioObject.jar
* `mv ./config.properties ./target/config.properties`
2.	Open Docker and run Kafka:
 * docker-compose up -d
 * docker-compose ps
3.	Run the SimService:
* (sudo) java -jar ./path_to/SimService/target/SimService-0.1-jar-with-dependencies.jar
4.	Run the SendScenarioObject with your scenario file as input
* (sudo) java -jar ./path_to/SimService/target/SendScenarioObject.jar ./path_to_scenario/scenario_file.json

## What to do to compile the SumoWrapper:
1.	Install sumo (make sure to check out a release-tag from the sumo-git-repo)
* https://sumo.dlr.de/docs/Installing/
* https://sumo.dlr.de/docs/Installing/Linux_Build.html
2.	Install missing libraries
* ([libserdes++](https://github.com/confluentinc/libserdes))
* [libavrocpp](https://github.com/apache/avro/blob/main/lang/c++/README),
* [librdkafka](https://github.com/confluentinc/librdkafka)
* ([libcppkafka](https://github.com/mfontanini/cppkafka))
* [pugixml](https://pugixml.org/docs/quickstart.html)
3.	Compile CppBaseWrapper
* mkdir build
* cd build
* cmake ..
* make
4.	Compile SumoWrapper
* Adjust Makefile
* Run make
5.	Make sure the paths in `_data\executables\SumoWrapper\run.sh` are correct before running a scenario
