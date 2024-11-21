# DaceDS4energy

## What to install

* The simulation service is implemented for Linux operating systems, it is highly recommended to use Linux Ubuntu distribution (22.04). If you want to use it on Windows, please install [WSL](https://learn.microsoft.com/de-de/windows/wsl/install) and run all the commands in the WSL (open the cmd and write bash to activate WSL)
* [JDK 11](https://jdk.java.net/archive/). 
  * set JAVA_Home
  * add %JAVA_HOME%\bin to your Path
* Install [Maven](https://maven.apache.org/download.cgi) and add it to your Path
* Install [Docker Desktop](https://docs.docker.com/engine/install/)
  * For Windows: Go to settings -> General and enable "Use the WSL 2 based engine"
  * For Linux: Go to settings -> General and enable "enable 'docker-compose' CLI alias" 
* Do step 1 of the [Setup Confluent Platform](https://docs.confluent.io/platform/current/platform-quickstart.html#qs-prereq)  using the [Zookeeper-compose file](https://github.com/confluentinc/cp-all-in-one/blob/7.5.2-post/cp-all-in-one/docker-compose.yml) instead of the wget command (if an error occurs during compose up -d check if the indentation of the yaml-file is correct)
* Navigate to Control Center at http://localhost:9021. It may take a minute or two for Control Center to start and load. Click the controlcenter.cluster tile.
* For Windows Users: If an error occurs during the installation of docker or confluent try:
  * dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
  * wsl --update


## How to compile DaceDS4energy
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
* Install SUMOLibraries in the parent directory (/../sumo) using https://github.com/DLR-TS/SUMOLibraries 
2.	Install missing libraries (Preferably in DaceDS folder)
   - Install **SUMOLibraries** in the parent directory (`/../sumo`) using this [guide](https://github.com/DLR-TS/SUMOLibraries).
   - Install the following libraries:
     - [Avro](https://github.com/apache/avro): Follow the [instructions](https://github.com/apache/avro/blob/main/lang/c++/README) for both `avro/lang/c++` and `avro/lang/c`.
     - [Libserdes](https://github.com/confluentinc/libserdes)
     - [Librdkafka](https://github.com/confluentinc/librdkafka)
     - [CppKafka](https://github.com/mfontanini/cppkafka)
     - [PugiXML](https://github.com/zeux/pugixml)

3. **Build Libraries**:
   - For **CppKafka** and **PugiXML**:
     ```bash
     mkdir build
     cd build
     cmake ..
     make -j5
     sudo make install
     ```
   - For **Librdkafka** and **Libserdes**:
     ```bash
     ./configure (#modify the `configure` script to use C++17 if build issues occur)
     make -j5
     sudo make install
     ```
 
3.	Compile CppBaseWrapper (adapt files in `CMakeLists.txt`)

     ```bash
     mkdir build
     cd build
     cmake ..
     make -j5
     ```
  
4.	Compile SumoWrapper
* Adjust `Makefile`
* Run `make`
5. Install gnome-terminal: `sudo apt install gnome-terminal`
6. Make sure the paths in `_data\executables\SumoWrapper\run.sh` are correct before running a scenario

## Running a PyPSA Scenario

1. **Install Python**: [Download Python](https://www.python.org/downloads/) and set it up.
2. **Install PyPSA**: Follow the [installation guide](https://pypsa-eur.readthedocs.io/en/latest/installation.html).
3. **Install Required Python Packages**:
   ```bash
   pip install confluent-kafka avro tables
   ```
4. Create a scenario file and place it in `_data/scenarios`.
5. Follow the general instructions in the **"Running a DaceDS Scenario"** section.

