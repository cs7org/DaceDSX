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
#include <stdexcept>

#include "main/SimulationWrapper.h"
#include "util/Config.h"
#include "util/Defines.h"

/**
* This class provides the generic orchestration interface description. 
*/

namespace daceDS {
class Orchestration {
   protected:
    std::shared_ptr<SimulationWrapper> wrapper;

   public:
    static std::vector<std::string> methods;
    static std::vector<std::string> getMethods() {
        return methods;
    }

    Orchestration(SimulationWrapper* w) : wrapper(w){};
    ~Orchestration(){};

    //this is layer independent
    virtual void ctrl(OrchestrationTopicMetadata& ometa, datamodel::CtrlMsg& ctrl) { throw EXCEPTION_NOT_IMPLEMENTED; };
//    virtual void status(OrchestrationTopicMetadata& ometa, datamodel::StatusMsg& state) { throw EXCEPTION_NOT_IMPLEMENTED; };
};
}  // namespace daceDS
