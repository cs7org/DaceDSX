/*
MIT License

Copyright 2021 Moritz Gütlein

This code was originally published under the Apache 2.0 License (http://www.apache.org/licenses/LICENSE-2.0) in 2021.
In 2025, it has been relicensed under the MIT License (https://choosealicense.com/licenses/mit/) with the explicit permission of all copyright holders.
*/

#include "SimulationControl.h"
using namespace daceDS;

void SimulationControl::addObserver(datamodel::Observer o) {
    KDEBUG(" Added Observer task=" << o.Task << " Element=" << o.Element << " Filter=" << o.Filter << " Period=" << o.Period << " Trigger=" << o.Trigger);
    observers.push_back(std::make_shared<Observer>(producer, o));
}

void SimulationControl::runObservers() {
    for (auto ob : observers) {
        ob->observe();
    }
}
