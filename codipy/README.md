# CoDiPy: Cooperative Downloading in Python
***
#### This project is used to simulate the Vehicle Communication for the use of data communication.

## Table of Contents
1. [General Info](#general-info)
2. [Simulation Run](#simulation-run)
3. [Installation](#installation)
4. [Documentation](#documentation)
5. [Collaboration](#collaboration)
6. [Citation](#citation)
7. [FAQs](#faqs)


<a name="general-info"></a>
### General Info
This projects simulates the V2V communication between vehicles to cooperatively download information from a backend. Additionally, WLAN APs can be places
in the vicinity of the street network to enable WLAN communication between the APs and the vehicles. 
Please see the code for further documentation and the availability of parameters for simulation.
This project contains a `m̀anhattan_grid` folder, containing example SUMO files with different vehicular densities (veh/km/lane).

A PPO and A2C Reinforcement Learning agent is contained for the use of RL with CoDiPy.
<a name="simulation-run"></a>
### Simulation Run

The parameters for a simulation can be set in `config.xml`.
Following fields are possible:

    - input
        - sumo-conifg (Path to SUMO config file)
        - sumo-path (Path to SUMO binary)
        - sumo-buildings (Path to SUMO buildings file)
        - sumo-polygons (Path to SUMO polygons file)
        - sumo-route (Path to SUMO route file)
        - sumo-network (Path to SUMO network file)
    - output
        - output-path (Path for simulation result files)
        - result-file-conversion (Result files are processed or not)
    - time
        - simulation-duration (Simulate a duration or a number of routes)
        - duration (Duration of simulation)
        - number-of-routes (Number of routes per vehicle)
    - communication
        - standard (The V2V communication standard to use)
        - mcs (Modulation and Coding Scheme)
    - constants
        - gain
        - transmission power
        - pathloss
        - noisepower
        - two-ray-ground
        - log-distance
        - log-normal-shadowing
        - log-normal-shadowing-dual-slope
        - loss-exponent
        - loss-exponent2
        - sigma
        - sigma2
        - antenna-height
    - parameter
        - v2v-distance (V2V communication distance)
        - number-vehicles (Number of communicating vehicles)
        - additional-vehicles (Number of additional vehicles in the simulation)
        - update-size (Size of update in Byte)
        - iterations (Number of iterations)
        - initial-seeds (Number of initial seeds)
        - ap-placement (Placement of WLAN APs)
        - v2v-device (Use of V2V communication)
        - wlan-device (Use of WLAN communication)
        - wlan-distance (Maximum WLAN communication distance)
        - wlan-beacon-interval (Time interval of WLAN beacons)
        - fixed-randomness (Fix the randomness)
        - wlan-heartbeat-strategy (WLAN Heartbeat Strategy)
        - v2v-heartbeat-interval (Interval of V2V Heartbeat messages)
        - wlan-data-rate (Data rate of WLAN)
        - v2v-data-rate (Data rate of V2V)
        - wlan-ap-count (Number of WLAN APs)
        - v2v-heartbeat-strategy (V2V Heartbeat Strategy)
        - heartbeat-encoding (Encoding of information in Heartbeat messages)
        - initial-seeds (Number of initial seeds)
        - seeding-strategy (Strategy for initial seeding)
        - additional-attenuation (Additional attenuation)
    - parameter-variation
        ! (One or multiple of the above options in 'parameter', exclusive 'iterations', multiple parameter values are possible, i.e. initial-seeds: 1000, 2000, 3000)
    - processing
        - processes (Number of processes to run in parallel)


<a name="installation"></a>
### Installation

#### SUMO
[SUMO - Simulation of Urban Mobility](https://www.eclipse.org/sumo/about/) is a mobility simulator.

Installation from the [GitHub Repository](https://github.com/eclipse/sumo) with:
    
`git clone --recursive https://github.com/DLR-TS/SUMOLibraries`
   
`sudo apt-get install cmake python g++ libxerces-c-dev libfox-1.6-dev libgdal-dev libproj-dev libgl2ps-dev swig`
   
`cd <SUMO_DIR> # please insert the correct directory name here`
   
`export SUMO_HOME="$PWD"`
   
`mkdir build/cmake-build && cd build/cmake-build`
   
`cmake ../..`
    
`make -j$(nproc)`

More information on build instructions can be found here: [https://sumo.dlr.de/docs/Developer/index.html#build_instructions](https://sumo.dlr.de/docs/Developer/index.html#build_instructions)

It is useful to add the SUMO_HOME variable in the path. See here: [https://sumo.dlr.de/docs/Installing/Linux_Build.html#definition_of_sumo_home](https://sumo.dlr.de/docs/Installing/Linux_Build.html#definition_of_sumo_home)

#### Python

Current development uses Python Version 3.11

Please install the packages in the `requirements.txt` file

#### Cython

Please run `python3.11 setup.py build_ext --inplace [--compiler=mingw32 #only for Windows!]` for compiling the Cython libraries.

#### InTAS

If you want to use the InTAS traffic install the GitHub project

Clone the [GitHub Repository](https://github.com/silaslobo/InTAS) of the InTAS project for the SUMO scenario.

Then, copy the `InTAS_network_traci_only.sumocfg` file into the folder `InTAS/scenario/`

to run a simulation  `python3.11 simulation_run.py -c path/to/config -p 0 -i 1 -s 50.0`

<a name="documentation"></a>
### Documentation

Build a documentary with the following steps:

Clone the [GitHub Repository](https://github.com/doxygen/doxygen) and follow the build instructions here: [https://www.doxygen.nl/manual/install.html#install_src_unix](https://www.doxygen.nl/manual/install.html#install_src_unix)

You can then use the binary `/build/bin/doxygen` and use the `Doxyfile` in `/docs/` to compile a documentation in Latex and HTML.



<a name="collaboration"></a>
### Collaboration

Please contact `michael.niebisch@fau.de` for any questions regarding the framework.

<a name="citation"></a>
### Citation
Please cite as: 
```plain
@INPROCEEDINGS{codipy,
  author={Niebisch, Michael and Pfaller, Daniel and Djanatliev, Anatoli},
  booktitle={2022 18th International Conference on Wireless and Mobile Computing, Networking and Communications (WiMob)}, 
  title={CoDiPy: Performance Evaluation of Vehicular Cooperative Downloading in Python}, 
  year={2022},
  volume={},
  number={},
  pages={461--465},
  doi={10.1109/WiMob55322.2022.9941695}}
```
<a name="faqs"></a>
### FAQs


