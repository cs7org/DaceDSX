*/*
MIT License

Copyright 2021 Moritz Gütlein

This code was originally published under the Apache 2.0 License (http://www.apache.org/licenses/LICENSE-2.0) in 2021.
In 2025, it has been relicensed under the MIT License (https://choosealicense.com/licenses/mit/) with the explicit permission of all copyright holders.
*/
#pragma once

#include <set>
#include "../util/log.h"
#include "../util/Defines.h"
#include "ConsumedMessage.h"
#include <librdkafka/rdkafkacpp.h>

#include <mutex>
/**
 * Each consumer uses a single messageHandler implementation to process incoming messages.
 * Used to implement handlers for orchestration, interaction, and provision channel.
*/
namespace daceDS {

   
class MessageHandler {
   public:
    MessageHandler(){};
    virtual ~MessageHandler(){};

    virtual bool handle(ConsumedMessage* msg) = 0;
    
    // struct cm_compare {
    //     bool operator() (const ConsumedMessage& a, const ConsumedMessage& b) const {
    //         return 1;
    //         if(a.st == b.st) {
    //             if(a.topic == b.topic) { 
    //                 if(a.key == b.key) { 
    //                     return a.sender < b.sender;
    //                 }
    //                 return a.key < b.key;
    //             }
    //             return a.topic < b.topic;

    //         }
    //         return a.st < b.st;
    //     }
    // };

    struct cm_compare {
        bool operator() (const ConsumedMessage* a, const ConsumedMessage* b) const {
            return 1;
            if(a->st == b->st) {
                if(a->topic == b->topic) { 
                    if(a->key == b->key) { 
                        return a->sender < b->sender;
                    }
                    return a->key < b->key;
                }
                return a->topic < b->topic;

            }
            return a->st < b->st;
        }
    };

    std::set<ConsumedMessage*, cm_compare> buffer;
    bool bufferConsumedMessage(ConsumedMessage* msg);
    void processBuffer(int time, int epoch);
};
}  // namespace daceDS
