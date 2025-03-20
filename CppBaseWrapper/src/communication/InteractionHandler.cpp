*/*
MIT License

Copyright 2021 Moritz Gütlein

This code was originally published under the Apache 2.0 License (http://www.apache.org/licenses/LICENSE-2.0) in 2021.
In 2025, it has been relicensed under the MIT License (https://choosealicense.com/licenses/mit/) with the explicit permission of all copyright holders.
*/
#include "InteractionHandler.h"
using namespace daceDS;

InteractionHandler::InteractionHandler(std::shared_ptr<Producer> p){
//    api = i;
    producer = p;
}

bool InteractionHandler::handle(ConsumedMessage* msg) {
    KDBGCB("Got msg on topic " << msg->topic);

    return true;
}