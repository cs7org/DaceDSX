/*
MIT License

Copyright 2021 Moritz Gütlein

This code was originally published under the Apache 2.0 License (http://www.apache.org/licenses/LICENSE-2.0) in 2021.
In 2025, it has been relicensed under the MIT License (https://choosealicense.com/licenses/mit/) with the explicit permission of all copyright holders.
*/

#include "api/Traffic/Micro/Orchestration.h"

namespace daceDS {
class OrchestrationImpl : public Orchestration {
   public:
    OrchestrationImpl(SimulationWrapper* w) : Orchestration(w){};
    ~OrchestrationImpl(){};
    void ctrl(OrchestrationTopicMetadata& ometa, datamodel::CtrlMsg& ctrl);
//    void status(OrchestrationTopicMetadata& ometa, datamodel::StatusMsg& state);
};
}  // namespace daceDS
