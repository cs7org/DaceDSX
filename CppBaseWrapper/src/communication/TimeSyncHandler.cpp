*/*
MIT License

Copyright 2021 Moritz Gütlein

This code was originally published under the Apache 2.0 License (http://www.apache.org/licenses/LICENSE-2.0) in 2021.
In 2025, it has been relicensed under the MIT License (https://choosealicense.com/licenses/mit/) with the explicit permission of all copyright holders.
*/
#include "TimeSyncHandler.h"
using namespace daceDS;

bool TimeSyncHandler::handle(ConsumedMessage* msg) {
    DS_SYNC_DBG("got msg in KafkaTimeSyncConsumer on topic=" << msg->topic);
    datamodel::SyncMsg sync = AvroHelper::getInstance()->decodeSyncMsg("payload", msg->payload, msg->len);
    // if(sync.Action==datamodel::ActionType::REQUEST){
    if (sync.Action == "request") {
        timeSync->handleTopicSyncMsgRequest(sync);
    }
    // if(sync.Action==datamodel::ActionType::JOIN){
    else if (sync.Action == "join") {
        timeSync->handleTopicSyncMsgJoin(sync);
    }
    // if(sync.Action==datamodel::ActionType::LEAVE){
    else if (sync.Action == "leave") {
        timeSync->handleTopicSyncMsgLeave(sync);
    } else {
        return false;
    }

    return true;
}
