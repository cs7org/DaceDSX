*/*
MIT License

Copyright 2021 Moritz Gütlein

This code was originally published under the Apache 2.0 License (http://www.apache.org/licenses/LICENSE-2.0) in 2021.
In 2025, it has been relicensed under the MIT License (https://choosealicense.com/licenses/mit/) with the explicit permission of all copyright holders.
*/
#pragma once

#include <csignal>
#include <iostream>
#include <stdexcept>
#include <thread>

#include "MessageHandler.h"
#include "api/Traffic/Micro/Orchestration.h"
#include "communication/AvroHelper.h"
#include "datamodel/CtrlMsg.hh"
#include "datamodel/StatusMsg.hh"
#include "datamodel/SyncMsg.hh"
#include "util/Config.h"
#include "util/Defines.h"
#include "util/log.h"

namespace daceDS {
class OrchestrationHandler : public MessageHandler {
    std::shared_ptr<Orchestration> api;

   public:
    OrchestrationHandler(std::shared_ptr<Orchestration> o) : MessageHandler() { api = o; };
    virtual ~OrchestrationHandler(){};

    bool handle(ConsumedMessage* msg) override;
};
}  // namespace daceDS
