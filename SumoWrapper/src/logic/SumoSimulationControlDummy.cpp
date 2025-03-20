*/*
MIT License

Copyright 2021 Moritz Gütlein

This code was originally published under the Apache 2.0 License (http://www.apache.org/licenses/LICENSE-2.0) in 2021.
In 2025, it has been relicensed under the MIT License (https://choosealicense.com/licenses/mit/) with the explicit permission of all copyright holders.
*/
#include "logic/SumoSimulationControlDummy.h"

using namespace daceDS;

void SumoSimulationControlDummy::init(SumoWrapper* w) {
//    traci = t;
//    wrapper = w;
}

void SumoSimulationControlDummy::run() {
//    int64_t fakeClock = wrapper->scenarioDescription.SimulationStart;
//    for (int64_t i = wrapper->scenarioDescription.SimulationStart; fakeClock < wrapper->scenarioDescription.SimulationEnd + 1;) {
//        try {
//            traci->setTime(fakeClock);
//
//            //post action phase
//            KDEBUG("runObservers: ");
//            runObservers();
//            KDEBUG("runObservers DONE ");
//
//        } catch (const std::exception& e) {
//            KDEBUG("runFederateLoop: Exception at border processing");
//            KDEBUG(e.what());
//        }
//    }
}

void SumoSimulationControlDummy::addObserver(datamodel::Observer o) {
//    observers.push_back(o);
}

void SumoSimulationControlDummy::runObservers() {
    //custom observers
//    for (datamodel::Observer ob : observers) {
//        KDEBUG(" Task=" << ob.Task << " Attribute=" << ob.Attribute << " Filter=" << ob.Filter << " Subject=" << ob.Subject << " Period=" << ob.Period << " Trigger=" << ob.Trigger);
//
//        if (ob.Task != "publish") continue;
//
//        traci->observe(ob);
//    }
//
//    //border observers
//    for (datamodel::Observer ob : borderObservers) {
//        KDEBUG("Running border observer for " << ob.Subject);
//        traci->observe(ob);
//    }
}
