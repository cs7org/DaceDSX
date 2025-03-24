*/*
MIT License

Copyright 2021 Moritz Gütlein

This code was originally published under the Apache 2.0 License (http://www.apache.org/licenses/LICENSE-2.0) in 2021.
In 2025, it has been relicensed under the MIT License (https://choosealicense.com/licenses/mit/) with the explicit permission of all copyright holders.
*/

#pragma once

#include <iostream>
#include <stdexcept>

#include "communication/Producer.h"
#include "datamodel/Observer.hh"
#include "util/Config.h"
#include "util/Defines.h"

/**
 * Interface for an observer.
 * Mght be inherited & extended by simulator wrappers.
*/
namespace daceDS {
class Observer {
   protected:
    std::shared_ptr<Producer> producer;
    std::string topic = "";

   public:
    datamodel::Observer observer;
    Observer(){};
    Observer(std::shared_ptr<Producer> p, datamodel::Observer o) {
        producer = p;
        observer = o;
    };
    ~Observer(){};

    virtual void observe(){};
};
}  // namespace daceDS
