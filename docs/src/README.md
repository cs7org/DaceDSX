# DaceDSX

 [![License: MIT](https://img.shields.io/badge/License-MIT%20%28with%20exceptions%29-yellow.svg)](https://opensource.org/licenses/MIT)

DaceDSX is a data-centric Distributed Simulation framework that focuses on data and loose couplings between components, with a focus on energy research. 
It enables to combine various black-boxes in a plug-and-play manner. 
The connection of simulators, the integrating of data sources, the provision of data & interaction interfaces for external components, as well as the orchestration of simulation runs is covered. 
All communication is realized via a topic-based publish/subscribe paradigm on top of Apache Kafka.

This repository based of [DaceDS](https://github.com/guetlein/daceDS) from Moritz Gütlein. In this repository we will further develop DaceDSX to improve its initial state and to match the needs of the energy research community.
In the future we will add more wrappers for simulators and new features. 
The planned extensions can be found in this [publication](https://doi.org/10.5281/zenodo.15064826).
