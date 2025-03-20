*/*
MIT License

Copyright 2021 Moritz Gütlein

This code was originally published under the Apache 2.0 License (http://www.apache.org/licenses/LICENSE-2.0) in 2021.
In 2025, it has been relicensed under the MIT License (https://choosealicense.com/licenses/mit/) with the explicit permission of all copyright holders.
*/
#pragma once

#include <map>
#include <string>
#include <vector>

#include "util/log.h"

/**
 * Generic producer class. Use a custom producer that inherits, 
 * in order to connect specific middlewares such as Kafka.
*/
namespace daceDS {
class Producer {
    bool counting = false;
    
   protected:
     std::string id;

   public:
    Producer(bool c = false) : counting(c){};
    ~Producer(){};

    virtual void init(std::string broker, std::vector<std::string> topics, std::string i, std::string loglevel = ""){};
    virtual bool createTopic(std::string topic) { return false; };

    virtual bool publish(std::string topic, std::string payload);
    virtual bool publish(std::string topic, std::string payload, int64_t time);
    virtual bool publish(std::string topic, std::string key, std::string payload, int64_t time, bool repeatOnError = false);

    virtual bool publish(std::string topic, std::vector<char>& payload, bool repeatOnError);
    virtual bool publish(std::string topic, std::vector<char>& payload);
    virtual bool publish(std::string topic, std::vector<char>& payload, int64_t time);
    virtual bool publish(std::string topic, std::string key, std::vector<char>& payload, int64_t time, bool repeatOnError = false);

    bool isCounting() { return counting; };
    static std::map<std::string, int64_t> countingSentMessages;
};
}  // namespace daceDS
