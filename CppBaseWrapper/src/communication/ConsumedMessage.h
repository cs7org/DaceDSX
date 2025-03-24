/*
MIT License

Copyright 2021 Moritz Gütlein

This code was originally published under the Apache 2.0 License (http://www.apache.org/licenses/LICENSE-2.0) in 2021.
In 2025, it has been relicensed under the MIT License (https://choosealicense.com/licenses/mit/) with the explicit permission of all copyright holders.
*/
#pragma once


#include <map>
#include <memory>
#include <regex>
#include <string>
#include <vector>


namespace daceDS {
    
class ConsumedMessage {


    public:

    std::string topic = "x";
    std::string key= "x";
    int64_t timestamp = 0;
    char * payload;
    size_t len = 0;
    std::string sender= "x";
    int64_t st = 0;
    ConsumedMessage(std::string topic, std::string key, int64_t timestamp, std::string sender, size_t len, int64_t st, void * payloadSrc) : topic(topic), key(key), timestamp(timestamp), sender(sender), len(len), st(st) {
        payload = new char[len];
        memcpy(payload, payloadSrc, len);
    };
    ~ConsumedMessage(){ delete[] payload;};
};
}