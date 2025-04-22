/*
MIT License

Copyright 2021 Moritz Gütlein

This code was originally published under the Apache 2.0 License (http://www.apache.org/licenses/LICENSE-2.0) in 2021.
In 2025, it has been relicensed under the MIT License (https://choosealicense.com/licenses/mit/) with the explicit permission of all copyright holders.
*/

#pragma once

#include <fstream>
#include <iomanip>
#include <map>
#include <sstream>
#include <string>
#include <vector>

#include "util/log.h"

namespace daceDS {
class Config {
   private:
    std::map<std::string, std::string> configParamMap;
    std::string scenarioID;
    std::string simulatorID;
    static Config* inst;

   public:
    Config();
    static Config* getInstance();
    void setScenarioID(std::string s);
    void setSimulatorID(std::string s);
    std::string getScenarioID();
    std::string getSimulatorID();

    bool readConfig(std::string path);

    std::string get(std::string key);
    void set(std::string key, std::string val);

    std::string getTopic(std::string channel, std::string topic);
    // std::string getAPITopic(std::string call);
    std::string getProvisionTopic(std::string c);
    std::string getProvisionBaseTopic(std::string c);
    std::string getOrchestrationTopic(std::string c);

    std::string getBaseDir();
    std::string getResourceDir();
    std::string getOutputDir();
    std::string getLogDir();

    // std::string getInteractionTopic(std::string c);
    std::string getInteractionTopic(std::string domain, std::string layer);
    std::string getProvisionTopic(std::string domain, std::string layer, std::string s);
    std::string getPersistentTopic(std::string subject, std::string entityId, std::string attribute);
};
}  // namespace daceDS
