/*
MIT License

Copyright 2021 Moritz Gütlein

This code was originally published under the Apache 2.0 License (http://www.apache.org/licenses/LICENSE-2.0) in 2021.
In 2025, it has been relicensed under the MIT License (https://choosealicense.com/licenses/mit/) with the explicit permission of all copyright holders.
*/
#include "ProvisionHandlerTrafficMicro.h"
using namespace daceDS;

bool ProvisionHandlerTrafficMicro::handle(ConsumedMessage* msg) {

    TopicMetadata meta = AvroHelper::getInstance()->getTopicMetadata(msg->topic);
    ProvisionHandler::handle(msg);
    ProvisionTopicMetadata pmeta = AvroHelper::getInstance()->getProvisionTopicMetadata(meta);
    
    if (pmeta.meta.channelSpecific.find("edge") != std::string::npos) {
        DS_BASE_DBG("Received traffic with key: " << msg->key);
        datamodel::Micro micro = AvroHelper::getInstance()->decodeMicro("payload", msg->payload, msg->len);
        DS_BASE_DBG("decoded micro");
        DS_BASE_DBG("micro.vehicleID="<<micro.vehicleID);
//        api->Provision::vehicle->traffic(pmeta, micro);
    } else {
        DS_BASE_DBG(pmeta.meta.channelSpecific << " is not supported");
        return false;
    }

    return true;
}
