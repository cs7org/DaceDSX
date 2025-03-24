*/*
MIT License

Copyright 2021 Moritz Gütlein

This code was originally published under the Apache 2.0 License (http://www.apache.org/licenses/LICENSE-2.0) in 2021.
In 2025, it has been relicensed under the MIT License (https://choosealicense.com/licenses/mit/) with the explicit permission of all copyright holders.
*/
#include "ProvisionHandler.h"
using namespace daceDS;

bool ProvisionHandler::handle(ConsumedMessage* msg) {

    //decode metadata for provision channel
    TopicMetadata meta = AvroHelper::getInstance()->getTopicMetadata(msg->topic);
    ProvisionTopicMetadata pmeta = AvroHelper::getInstance()->getProvisionTopicMetadata(meta);
    DS_BASE_DBG("Got msg in KafkaProvisionConsumer: " << pmeta.meta.channelSpecific << " on topic " << msg->topic);

    //parse different packages depending on topic
    if (pmeta.meta.channelSpecific == "scenario") {
        DS_BASE_DBG("Got scenario description");
        datamodel::Scenario r = AvroHelper::getInstance()->decodeScenario("payload", msg->payload, msg->len);
        DS_BASE_DBG("Scenario is decoded");
        api->scenario(pmeta, r);
        return true;
    }

    else if (pmeta.meta.channelSpecific == "resource") {
        DS_BASE_DBG("Received resourceFile");
        datamodel::ResourceFile r = AvroHelper::getInstance()->decodeResourceFile("payload", msg->payload, msg->len);
        DS_BASE_DBG("ResourceFile is decoded");
        api->resource(pmeta, r);
        return true;
    }
    

    return false;
}
