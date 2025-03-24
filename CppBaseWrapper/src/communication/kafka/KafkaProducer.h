/*
MIT License

Copyright 2021 Moritz Gütlein

This code was originally published under the Apache 2.0 License (http://www.apache.org/licenses/LICENSE-2.0) in 2021.
In 2025, it has been relicensed under the MIT License (https://choosealicense.com/licenses/mit/) with the explicit permission of all copyright holders.
*/
#pragma once

#include <rdkafkacpp.h>

#include <iostream>
#include <map>
#include <stdexcept>

#include "communication/Producer.h"
#include "util/Config.h"
#include "util/log.h"

using std::cin;
using std::cout;
using std::endl;
using std::exception;
using std::getline;
using std::string;

/**
 * Based on the cppkafka examples
 * */

namespace daceDS {
class KafkaProducer : public Producer {
    RdKafka::Producer* producer;
    RdKafka::Conf* conf;
    std::map<std::string, RdKafka::Topic*> topicMap;
    static std::map<std::string, int64_t> sentMessages;

   public:
    KafkaProducer(bool counting = false) : Producer(counting){};
    ~KafkaProducer() { delete producer; };

    void init(std::string broker, std::vector<std::string> topics, string i, string loglevel = "");
    bool createTopic(std::string topic);

    virtual bool publish(std::string topic, std::string payload);
    virtual bool publish(std::string topic, std::string payload, int64_t time);
    virtual bool publish(std::string topic, std::string key, std::string payload, int64_t time, bool repeatOnError = false);

    bool publish(std::string topic, std::vector<char>& payload, bool repeatOnError);
    bool publish(std::string topic, std::vector<char>& payload);
    bool publish(std::string topic, std::vector<char>& payload, int64_t time);
    bool publish(std::string topic, std::string key, std::vector<char>& payload, int64_t time, bool repeatOnError = false);

};
}  // namespace daceDS
