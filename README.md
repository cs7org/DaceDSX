# DaceDSX

This repository is a new version of DaceDS from Moritz Gütlein. 
DaceDS is a data-centric Distributed Simulation framework that focuses on data and loose couplings between components. 
It enables to combine various black-boxes in a plug-and-play manner. 
The connection of simulators, the integrating of data sources, the provision of data & interaction interfaces for external components, as well as the orchestration of simulation runs is covered. 
All communication is realized via a topic-based publish/subscribe paradigm on top of Apache Kafka.

In this repository we will further develop DaceDSX to improve its initial state and to match the needs of the energy research community.
In the future we will add more wrappers for simulators and new features. 
The planned extensions can be found in this [publication](https://doi.org/10.5281/zenodo.15064826).
In the following you will find a guide on how to install and run DaceDSX with the implemented wrappers.
Further we provide a contribution guide and information on the licensing and publications.

# Installation guide
## What to install

* The simulation service is implemented for Linux operating systems, it is highly recommended to use Linux Ubuntu distribution (22.04). If you want to use it on Windows, please install [WSL](https://learn.microsoft.com/de-de/windows/wsl/install) and run all the commands in the WSL (open the cmd and write bash to activate WSL)
* [JDK 11](https://jdk.java.net/archive/). 
  * set JAVA_Home
  * add %JAVA_HOME%\bin to your Path
* Install [Maven](https://maven.apache.org/download.cgi) and add it to your Path
* For Windows Users: Install [WSL](https://learn.microsoft.com/de-de/windows/wsl/install)
* Install [Docker Desktop](https://docs.docker.com/engine/install/)
  * For Windows: Go to settings -> General and enable "Use the WSL 2 based engine"
  * For Linux: Go to settings -> General and enable "enable 'docker-compose' CLI alias" 
* Do step 1 of the [Setup Confluent Platform](https://docs.confluent.io/platform/current/platform-quickstart.html#qs-prereq)  using the [Zookeeper-compose file](https://github.com/confluentinc/cp-all-in-one/blob/7.5.2-post/cp-all-in-one/docker-compose.yml) instead of the wget command (if an error occurs during compose up -d check if the indentation of the yaml-file is correct)
* Navigate to Control Center at http://localhost:9021. It may take a minute or two for Control Center to start and load. Click the controlcenter.cluster tile.
* For Windows Users: If an error occurs during the installation of docker or confluent try:
  * dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
  * wsl --update


## How to compile DaceDSX
1. Download or check-out this repo
2. Compile the JavaBaseWrapper and SimService (just run “mvn install” in that folder, where pom.xml resides)
3. If any error occured with Build, please run “mvn install -Dhttps.protocols=TLSv1.2” (based on JDK 11 version)
4. Compile (if necessary) the Wrapper-folder, e.g. as shown below for SumoWrapper


## What to do to run a Scenario in DaceDSX:
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
* Create an empty config.h file and add it to the build folder in sumo
* Install **SUMOLibraries** in the parent directory (`/../sumo`) using this [guide](https://github.com/DLR-TS/SUMOLibraries).
2.	Install missing libraries (Preferably in DaceDSX folder)
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

## What to do to run a PyPSA-scenario:

1. **Install Python**: [Download Python](https://www.python.org/downloads/) and set it up.
2. **Install PyPSA**: Follow the [installation guide](https://pypsa-eur.readthedocs.io/en/latest/installation.html).
3. **Install Required Python Packages**:
   ```bash
   pip install confluent-kafka avro tables
   ```
4. Create a scenario file and place it in `_data/scenarios`.
5. Follow the general instructions in the **"What to do to run a Scenario in DaceDSX"** section.


# Further information
## How to Contribute
You are welcome to contribute to DaceDSX via bug reports and feature requests at any time.

## License
This project is primarily licensed under the MIT License. However, files in the `CppBaseWrapper/src/datamodel/` directory and the file `PythonWrapper/src/communication/AvroProducerConsumer.py` remain under the Apache License 2.0.
You can find further information on the MIT License in the [LICENSE](./LICENSE)-file or on this [website](https://choosealicense.com/licenses/mit/).
For mor information on the Apache License 2.0 take a look at the [LICENSE-APACHE](./CppBaseWrapper/src/datamodel/LICENSE-APACHE)-file or on this [website](https://www.apache.org/licenses/LICENSE-2.0).

## Publications

Main conceptual ideas can be found in the following publications:

- Seiwerth, C., Halikulov, N., & German, R. (2025, März 21). Extending a Data-Centric Distributed Simulation Framework for the Energy Domain. 2. NFDI4Energy Conference, Karlsruhe. https://doi.org/10.5281/zenodo.15064826
- M. Gütlein and A. Djanatliev, "On-demand Simulation of Future Mobility Based on Apache Kafka," in Simulation and Modeling Methodologies, Technologies and Applications, ser. Lecture Notes in Networks and Systems, M. S. OBAIDAT, T. OREN, and F. D. RANGO, Eds. Cham: Springer International Publishing, 2022, pp. 18–41.
- M. Gütlein, R. German , and A. Djanatliev, "Hide Your Model! Layer Abstractions for Data-Driven Co-Simulations," in 2021 Winter Simulation Conference (WSC). IEEE, Dec. 2021, pp. 1–12.
- M. Gütlein, W. Baron, C. Renner, and A. Djanatliev, ``Performance Evaluation of HLA RTI Implementations," in 2020 IEEE/ACM 24th International Symposium on Distributed Simulation and Real Time Applications (DS-RT). IEEE, Sep. 2020, pp. 1–8.
- M. Gütlein and A. Djanatliev, "Modeling and Simulation as a Service using Apache Kafka:," in Proceedings of the 10th International Conference on Simulation and Modeling Methodologies, Technologies and Applications. SCITEPRESS - Science and Technology Publications, 2020, pp. 171–180.
- M. Gütlein and A. Djanatliev , "Coupled Traffic Simulation by Detached Translation Federates: An HLA-Based Approach," in 2019 Winter Simulation Conference (WSC). National Harbor, MD, USA: IEEE, Dec. 2019, pp. 1378–1389.
- M. Gütlein, R. German , and A. Djanatliev , "Towards a Hybrid Co-simulation Framework: HLA-Based Coupling of MATSim and SUMO," in 2018 IEEE/ACM 22nd International Symposium on Distributed Simulation and Real Time Applications (DS-RT).IEEE, 2018, pp. 1–9.
