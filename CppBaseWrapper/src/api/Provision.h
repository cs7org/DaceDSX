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


namespace daceDS {
class SimulationWrapper;
class Provision {
   protected:
    std::shared_ptr<SimulationWrapper> wrapper;

   public:
    static std::vector<std::string> methods;
    static std::vector<std::string> getMethods() {
        return methods;
    }

    int bla = 42;
    Provision(std::shared_ptr<SimulationWrapper> w) : wrapper(w){};
    Provision(){};
    ~Provision(){};

    //this is layer independent
    virtual void resource(ProvisionTopicMetadata& pmeta, datamodel::ResourceFile& r) { throw EXCEPTION_NOT_IMPLEMENTED; };
    virtual void scenario(ProvisionTopicMetadata& pmeta, datamodel::Scenario& r) { throw EXCEPTION_NOT_IMPLEMENTED; };

};
}  // namespace daceDS
