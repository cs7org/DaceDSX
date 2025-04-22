/*
MIT License

Copyright 2021 Moritz Gütlein

This code was originally published under the Apache 2.0 License (http://www.apache.org/licenses/LICENSE-2.0) in 2021.
In 2025, it has been relicensed under the MIT License (https://choosealicense.com/licenses/mit/) with the explicit permission of all copyright holders.
*/
#pragma once

#include <iostream>
#include <stdexcept>


#ifdef USING_TRACI
    #include "SumoConnectionTraCI.h"
#else
    #include "SumoConnectionLibSUMO.h"
#endif

#include "communication/kafka/KafkaProducer.h"
#include "cppkafka/message.h"
#include "datamodel/Micro.hh"
#include "logic/Observer.h"

namespace daceDS {
class SUMO_API_MODE;

class SumoObserver : public Observer {




    std::shared_ptr<SUMO_API_MODE> sumoConnection = nullptr;
    // std::shared_ptr<SumoConnectionLibSUMO> sumoConnection = nullptr;

    //time stepped
    int64_t observeTime = -1;
    bool repeatOnError = false;
    std::map<std::string, std::string> persistentTopics;

   public:
    SumoObserver(std::shared_ptr<Producer> p, datamodel::Observer o, std::shared_ptr<SUMO_API_MODE> s);
    // SumoObserver(std::shared_ptr<Producer> p, datamodel::Observer o, std::shared_ptr<SumoConnectionLibSUMO> s);
    ~SumoObserver(){};

    //time stepped
    bool observe(int64_t time);

    //needed for each valid subject:
    bool observeVehicle();
    bool observeEdge();
    //bool observeGeneric();
    bool observeDetector();

    //various sender functions
    template <typename T>
    bool send(std::string key, T value);

    bool sendAsJSON(std::string topic, std::string key, std::string value);
    bool sendAsJSON(std::string topic, std::string key, std::vector<std::string> value);
    bool sendAsJSON(std::string topic, std::string key, std::vector<double> value);
    bool sendAsJSON(std::string topic, std::string key, std::vector<datamodel::Micro> value);
    bool sendAsJSON(std::string topic, std::string key, double value);
    bool sendAsJSON(std::string topic, std::string key, int value);
    bool sendAsJSON(std::string topic, std::string key, Vec3D value);
    bool sendAsJSON(std::string topic, std::string key, datamodel::Micro value);
    bool sendAsJSON(std::string topic, std::string key, datamodel::MicroEdge value);
    bool sendAsJSON(std::string topic, std::string key, datamodel::MicroDetector value);

    bool sendAsAvro(std::string topic, std::string key, std::string value);
    bool sendAsAvro(std::string topic, std::string key, std::vector<std::string> value);
    bool sendAsAvro(std::string topic, std::string key, std::vector<double> value);
    bool sendAsAvro(std::string topic, std::string key, std::vector<datamodel::Micro> value);
    bool sendAsAvro(std::string topic, std::string key, double value);
    bool sendAsAvro(std::string topic, std::string key, int value);
    bool sendAsAvro(std::string topic, std::string key, Vec3D value);
    bool sendAsAvro(std::string topic, std::string key, datamodel::Micro value);
    bool sendAsAvro(std::string topic, std::string key, datamodel::MicroEdge value);
    bool sendAsAvro(std::string topic, std::string key, datamodel::MicroDetector value);

    //helpers
    void filterEntities(std::vector<std::string> &subjects);
    void filterInternalEntities(std::vector<string> &subjects);
    std::string getPersistentTopic(std::string entityId);
    bool isPersistentSubject();
};
}  // namespace daceDS
