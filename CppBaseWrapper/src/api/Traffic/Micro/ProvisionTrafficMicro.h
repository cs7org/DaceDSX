/*
MIT License

Copyright 2021 Moritz Gütlein

This code was originally published under the Apache 2.0 License (http://www.apache.org/licenses/LICENSE-2.0) in 2021.
In 2025, it has been relicensed under the MIT License (https://choosealicense.com/licenses/mit/) with the explicit permission of all copyright holders.
*/
#pragma once

#include <exception>
#include <iostream>
#include <memory>
#include <mutex>
#include <stdexcept>

#include "datamodel/Micro.hh"
#include "datamodel/ResourceFile.hh"
#include "datamodel/Scenario.hh"
#include "datamodel/BB.hh"
#include "main/SimulationWrapper.h"
#include "util/Config.h"
#include "util/Defines.h"

/**
* This class is derived from the traffic.micro layer definition. 
* As this is a generic interface description, this class will be 
* inherited by a wrapper for a tool that is categorized as 
* traffic.micro.
*/

#include "api/Provision.h"

namespace daceDS {
    
class ProvisionTrafficMicro : public Provision {

   public:

    ProvisionTrafficMicro(std::shared_ptr<SimulationWrapper> w) : Provision(w){};
    virtual ~ProvisionTrafficMicro(){};


    // //this is layer specific
    class Vehicle {
        std::vector<datamodel::Micro> incomingVehicles;

        std::mutex iVm;

       public:
        virtual void traffic(ProvisionTopicMetadata& pmeta, datamodel::Micro& m) { throw EXCEPTION_NOT_IMPLEMENTED; };

        virtual std::vector<datamodel::Micro> getAndClearIncomingVehicles() {
            std::unique_lock<std::mutex> lck(iVm);
            std::vector<datamodel::Micro> tmp = incomingVehicles;
            incomingVehicles.clear();
            lck.unlock();
            return tmp;
        };

        virtual void addIncomingVehicle(datamodel::Micro m) {
            std::unique_lock<std::mutex> lck(iVm);
            incomingVehicles.push_back(m);
            lck.unlock();
        };

    };
    std::unique_ptr<Vehicle> vehicle;
};
}  // namespace daceDS
