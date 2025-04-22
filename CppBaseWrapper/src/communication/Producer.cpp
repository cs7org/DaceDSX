/*
MIT License

Copyright 2021 Moritz Gütlein

This code was originally published under the Apache 2.0 License (http://www.apache.org/licenses/LICENSE-2.0) in 2021.
In 2025, it has been relicensed under the MIT License (https://choosealicense.com/licenses/mit/) with the explicit permission of all copyright holders.
*/
#include "Producer.h"
using namespace daceDS;

std::map<std::string, int64_t> Producer::countingSentMessages;

bool Producer::publish(std::string topic, std::string payload) {
    return false;
}

bool Producer::publish(std::string topic, std::string payload, int64_t time) {
    return false;
}

bool Producer::publish(std::string topic, std::string key, std::string payload, int64_t time, bool repeatOnError) {
    if (!isCounting()) {
        KDBGCB("Published to " << topic << " --> not counting");
        return false;
    }

    KDBGCB("Published to " << topic << " --> counting");
    if (Producer::countingSentMessages.count(topic) == 0) {
        Producer::countingSentMessages[topic] = 0;
    }
    Producer::countingSentMessages[topic]++;
    return false;
}

bool Producer::publish(std::string topic, std::vector<char>& payload, bool repeatOnError) {
    return false;
}

bool Producer::publish(std::string topic, std::vector<char>& payload) {
    return false;
}

bool Producer::publish(std::string topic, std::vector<char>& payload, int64_t time) {
    return false;
}

bool Producer::publish(std::string topic, std::string key, std::vector<char>& payload, int64_t time, bool repeatOnError) {
    if (!isCounting()) {
        KDBGCB("Published to " << topic << " --> not counting");
        return false;
    }

    KDBGCB("Published to " << topic << " --> counting");
    if (Producer::countingSentMessages.count(topic) == 0) {
        Producer::countingSentMessages[topic] = 0;
    }
    Producer::countingSentMessages[topic]++;
    return false;
}
