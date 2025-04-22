/*
MIT License

Copyright 2021 Moritz Gütlein

This code was originally published under the Apache 2.0 License (http://www.apache.org/licenses/LICENSE-2.0) in 2021.
In 2025, it has been relicensed under the MIT License (https://choosealicense.com/licenses/mit/) with the explicit permission of all copyright holders.
*/
#pragma once

#include <limits.h>
#include <stdio.h>
#include <sys/wait.h>
#include <unistd.h>

#include <algorithm>
#include <chrono>
#include <cwchar>
#include <iostream>
#include <locale>
#include <map>
#include <string>

#include "api/Provision.h"
#include "communication/Consumer.h"
#include "communication/Producer.h"
#include "logic/SimulationControl.h"
#include "logic/TimeSync.h"
#include "util/Config.h"
#include "util/Defines.h"
#include "util/Utils.h"
#include "util/log.h"

namespace daceDS {
class SimulationControl;
class Provision;

class SimulationWrapper {
    
   public:
    SimulationWrapper(std::string s, std::string t) : scenarioID(s), simulatorID(t){};
    virtual ~SimulationWrapper(){};

    virtual void runWrapper(){};
    virtual void endWrapper(){};
    virtual void killWrapper(){};

    std::shared_ptr<Producer> producer;
    std::shared_ptr<Provision> provision;
    std::shared_ptr<TimeSync> timeSync;
    std::shared_ptr<SimulationControl> ctrl;

    std::unique_ptr<Consumer> provisionConsumer = nullptr;
    std::unique_ptr<Consumer> orchestrationConsumer = nullptr;
    std::unique_ptr<Consumer> interactionConsumer = nullptr;

    std::string getID() { return scenarioID + "_" + simulatorID; }
    std::string getID(std::string suf) { return getID() + suf; }

    std::string scenarioID = "not_initialized";   //has to be known before resources can be received
    std::string simulatorID = "not_initialized";  //has to be known before resources can be received
};
}
