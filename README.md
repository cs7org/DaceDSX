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
* Do step 1 of the [Setup Confluent Platform](https://docs.confluent.io/platform/current/platform-quickstart.html#qs-prereq)  using the [Zookeeper-compose file](https://github.com/confluentinc/cp-all-in-one/blob/7.5.2-post/cp-all-in-one/docker-compose.yml) instead of the wget command (if an error occurs during compose up -d check if the indentation of the yaml-file is correct)
* For Windows Users: If an error occurs during the installation of docker or confluent try:
  * dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
  * wsl --update


## How to compile DaceDS
1. Download or check-out this repo
2. Compile the JavaBaseWrapper and SimService (just run “mvn install” in that folder, where pom.xml resides)
3. If any error occured with Build, please run “mvn install -Dhttps.protocols=TLSv1.2” (based on JDK 11 version)
4. Compile (if necessary) the Wrapper-folder, e.g. as shown below for SumoWrapper


## What to do to run a Scenario in DaceDS:
1.	Make sure a config.properties is next to the SimService-0.1-jar-with-dependencies.jar and SendScenarioObject.jar
* `mv ./config.properties ./target/config.properties`
* adapt the paths in the config.properties file
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
* export CMAKE_PREFIX_PATH=path_to_sumo_build/sumo/build:$CMAKE_PREFIX_PATH
* create an empty config.h file and add it to the build folder in sumo
2.	Install missing libraries (Preferably in DaceDS folder)
* [libavrocpp](https://github.com/apache/avro/blob/main/lang/c++/README), (make the installation under lang/c++) also install avro_c the same way
* [libserdes++](https://github.com/confluentinc/libserdes)
* [librdkafka](https://github.com/confluentinc/librdkafka)
* [libcppkafka](https://github.com/mfontanini/cppkafka)
* [pugixml](https://pugixml.org/docs/quickstart.html) run the following commands after download:
  * mkdir build
  * cd build
  * cmake ..
  * make -j5
  * sudo make install 
3.	Compile CppBaseWrapper (adapt files in CMakeList.txt)
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
