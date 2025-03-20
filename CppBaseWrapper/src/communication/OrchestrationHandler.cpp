*/*
MIT License

Copyright 2021 Moritz Gütlein

This code was originally published under the Apache 2.0 License (http://www.apache.org/licenses/LICENSE-2.0) in 2021.
In 2025, it has been relicensed under the MIT License (https://choosealicense.com/licenses/mit/) with the explicit permission of all copyright holders.
*/
#include "OrchestrationHandler.h"
using namespace daceDS;

bool OrchestrationHandler::handle(ConsumedMessage* msg) {
    //decode metadata for orchestration channel
    TopicMetadata meta = AvroHelper::getInstance()->getTopicMetadata(msg->topic);
    OrchestrationTopicMetadata ometa = AvroHelper::getInstance()->getOrchestrationTopicMetadata(meta);

    KERROR("orch msg on " << msg->topic);
    if (ometa.command == Command::CONTROL) {
//        datamodel::CtrlMsg ctrl = AvroHelper::getInstance()->decodeCtrlMsg("payload", msg->payload, msg->len);
//        api->ctrl(ometa, ctrl);
    } else if (ometa.command == Command::STATUS) {
//        datamodel::StatusMsg state = AvroHelper::getInstance()->decodeStatusMsg("payload", msg->payload, msg->len);
//        api->status(ometa, state);
    } else {
        KERROR("no valid command on topic=" << msg->topic);
        KERROR("no valid command on topic=" << msg->topic);
        KERROR("no valid command on topic=" << msg->topic);
        return false;
    }

    return true;
}
