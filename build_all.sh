#!/bin/bash
cd SimService
mvn clean install
cd ..
cd  CppBaseWrapper
make -j5
cd ..
cd SumoWrapper
make -j5
cd ..
cd Projectors/V2XProjector
mvn clean install
cd ..
cd ..
cd OppWrapper/Wrapper/src
make -j5
