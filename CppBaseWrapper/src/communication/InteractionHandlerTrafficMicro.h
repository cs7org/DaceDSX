/*
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

#include "InteractionHandler.h"
//#include "api/Traffic/Micro/Interaction.h"
#include "communication/AvroHelper.h"
#include "communication/Producer.h"
#include "communication/ConsumedMessage.h"
#include "cppkafka/configuration.h"
#include "cppkafka/consumer.h"
#include "cppkafka/utils/consumer_dispatcher.h"
#include "datamodel/SyncMsg.hh"
#include "util/Config.h"
#include "util/Defines.h"
#include "util/log.h"

namespace daceDS {

class Producer;

class InteractionHandlerTrafficMicro : public InteractionHandler {
   protected:
   std::shared_ptr<Producer> producer;

   public:
    InteractionHandlerTrafficMicro(std::shared_ptr<Producer> p);

    ~InteractionHandlerTrafficMicro(){};

    bool handle(ConsumedMessage* msg) override;
    void parseScopeVehicle(ConsumedMessage* msg, InteractionTopicMetadata2& imeta);
    void parseScopeWorld(ConsumedMessage* msg, InteractionTopicMetadata2& imeta);
};
}  // namespace daceDS
