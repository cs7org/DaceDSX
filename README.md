# DaceDSX

 [![Docs](https://img.shields.io/badge/Documentation-555555)](https://dacedsx.readthedocs.io/)
 [![License: MIT](https://img.shields.io/badge/License-MIT%20%28with%20exceptions%29-yellow.svg)](https://opensource.org/licenses/MIT)

DaceDSX is a data-centric Distributed Simulation framework that focuses on data and loose couplings between components, with a focus on energy research. 
It enables to combine various black-boxes in a plug-and-play manner. 
The connection of simulators, the integrating of data sources, the provision of data & interaction interfaces for external components, as well as the orchestration of simulation runs is covered. 
All communication is realized via a topic-based publish/subscribe paradigm on top of Apache Kafka.

This repository based of [DaceDS](https://github.com/guetlein/daceDS) from Moritz Gütlein. In this repository we will further develop DaceDSX to improve its initial state and to match the needs of the energy research community.
In the future we will add more wrappers for simulators and new features. 
The planned extensions can be found in this [publication](https://doi.org/10.5281/zenodo.15064826).

## Quickstart  Guide
Refer to the [**docs**](https://dacedsx.readthedocs.io/01-quickstart.html).

## License
This project is primarily licensed under the MIT License. Exceptions and further informations are listed in LICENSE.

## Publications

Main conceptual ideas can be found in the following publications:

- Seiwerth, C., Halikulov, N., & German, R. (2025, März 21). Extending a Data-Centric Distributed Simulation Framework for the Energy Domain. 2. NFDI4Energy Conference, Karlsruhe. https://doi.org/10.5281/zenodo.15064826
- M. Gütlein and A. Djanatliev, "On-demand Simulation of Future Mobility Based on Apache Kafka," in Simulation and Modeling Methodologies, Technologies and Applications, ser. Lecture Notes in Networks and Systems, M. S. OBAIDAT, T. OREN, and F. D. RANGO, Eds. Cham: Springer International Publishing, 2022, pp. 18–41.
- M. Gütlein, R. German , and A. Djanatliev, "Hide Your Model! Layer Abstractions for Data-Driven Co-Simulations," in 2021 Winter Simulation Conference (WSC). IEEE, Dec. 2021, pp. 1–12.
- M. Gütlein, W. Baron, C. Renner, and A. Djanatliev, ``Performance Evaluation of HLA RTI Implementations," in 2020 IEEE/ACM 24th International Symposium on Distributed Simulation and Real Time Applications (DS-RT). IEEE, Sep. 2020, pp. 1–8.
- M. Gütlein and A. Djanatliev, "Modeling and Simulation as a Service using Apache Kafka:," in Proceedings of the 10th International Conference on Simulation and Modeling Methodologies, Technologies and Applications. SCITEPRESS - Science and Technology Publications, 2020, pp. 171–180.
- M. Gütlein and A. Djanatliev , "Coupled Traffic Simulation by Detached Translation Federates: An HLA-Based Approach," in 2019 Winter Simulation Conference (WSC). National Harbor, MD, USA: IEEE, Dec. 2019, pp. 1378–1389.
- M. Gütlein, R. German , and A. Djanatliev , "Towards a Hybrid Co-simulation Framework: HLA-Based Coupling of MATSim and SUMO," in 2018 IEEE/ACM 22nd International Symposium on Distributed Simulation and Real Time Applications (DS-RT).IEEE, 2018, pp. 1–9.
