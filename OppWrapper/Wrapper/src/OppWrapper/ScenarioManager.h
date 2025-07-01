//
// Copyright (C) 2006-2017 Christoph Sommer <sommer@ccs-labs.org>
//
// Documentation for these modules is at http://veins.car2x.org/
//
// SPDX-License-Identifier: GPL-2.0-or-later
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program; if not, write to the Free Software
// Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
//

#pragma once

#include "OppWrapper.h"
#include "veins/modules/mobility/traci/VehicleSignal.h"
#include "veins/modules/mobility/traci/TraCIScenarioManager.h"
#include "veins/modules/mobility/traci/TraCIMobility.h"

#include "datamodel/Micro.hh"

namespace daceDS {


class ScenarioManager : public cSimpleModule {
public:
    ScenarioManager();
    ~ScenarioManager() override;

    void initialize(int stage) override;
    void init();
    void handleMessage(cMessage* msg) override;
    void handleSelfMsg(cMessage* msg);
    void executeOneTimestep();
    void processVehicleSubscription(daceDS::datamodel::Micro& micro);
    void processSubcriptionResult();
    void processSendMsgRequest(daceDS::datamodel::RadioMsg& msg);
    void processSendMsgRequests();

    std::shared_ptr<daceDS::OppWrapper> kafkaConnection;
    std::string host;
    std::string scenarioID;
    std::string simulatorID;
    int port;



    //FROM TRACISCENMAN
    //todo remove/replace all
    static const simsignal_t traciInitializedSignal;
    static const simsignal_t traciModuleAddedSignal;
    static const simsignal_t traciModuleRemovedSignal;
    static const simsignal_t traciTimestepBeginSignal;
    static const simsignal_t traciTimestepEndSignal;

    bool traciInitialized = false; /**< Flag indicating whether the init_traci routine has been run. Note that it will change to false again once set, even during shutdown. */
    simtime_t connectAt; /**< when to connect to TraCI server (must be the initial timestep of the server) */
    simtime_t firstStepAt; /**< when to start synchronizing with the TraCI server (-1: immediately after connecting) */
    simtime_t updateInterval; /**< time interval of hosts' position updates */
    cMessage* connectAndStartTrigger; /**< self-message scheduled for when to connect to TraCI server and start running */
    cMessage* executeOneTimestepTrigger; /**< self-message scheduled for when to next call executeOneTimestep */

    //veins::BaseWorldUtility* world;
    //std::map<const veins::BaseMobility*, const veins::MobileHostObstacle*> vehicleObstacles;
    //veins::VehicleObstacleControl* vehicleObstacleControl;
    double penetrationRate;
    bool autoShutdownTriggered;
    size_t nextNodeVectorIndex; /**< next OMNeT++ module vector index to use */
    std::map<std::string, cModule*> hosts; /**< vector of all hosts managed by us */
    std::set<std::string> unEquippedHosts;
    std::set<std::string> subscribedVehicles; /**< all vehicles we have already subscribed to */

    std::vector<std::string> updatedVIDs;

    bool isConnected() const
        {
            return static_cast<bool>(kafkaConnection);
        }

    cModule* getManagedModule(std::string nodeId) {
        if (hosts.find(nodeId) == hosts.end()) return nullptr;
        return hosts[nodeId];
    };

    // maps from vehicle type to moduleType, moduleName, and moduleDisplayString
    typedef std::map<std::string, std::string> TypeMapping;
    TypeMapping moduleType; /**< module type to be used in the simulation for each managed vehicle */
    TypeMapping moduleName; /**< module name to be used in the simulation for each managed vehicle */
    TypeMapping moduleDisplayString; /**< module displayString to be used in the simulation for each managed vehicle */


    void finish()
    {
        while (hosts.begin() != hosts.end()) {
            deleteManagedModule(hosts.begin()->first);
        }
    };


    void addModule(std::string nodeId, std::string type, std::string name, std::string displayString, const veins::Coord& position, std::string road_id = "", double speed = -1, veins::Heading heading = veins::Heading::nan, veins::VehicleSignalSet signals = {veins::VehicleSignal::undefined}, double length = 0, double height = 0, double width = 0){

//        cout << "KAfkaScenarioManager::addModule()" << endl;
        if (hosts.find(nodeId) != hosts.end()) throw cRuntimeError("tried adding duplicate module");

        double option1 = hosts.size() / (hosts.size() + unEquippedHosts.size() + 1.0);
        double option2 = (hosts.size() + 1) / (hosts.size() + unEquippedHosts.size() + 1.0);

//        if (fabs(option1 - penetrationRate) < fabs(option2 - penetrationRate)) {
//            unEquippedHosts.insert(nodeId);
//            return;
//        }

        int32_t nodeVectorIndex = nextNodeVectorIndex++;

        cModule* parentmod = getParentModule();
        if (!parentmod) throw cRuntimeError("Parent Module not found");

        cModuleType* nodeType = cModuleType::get(type.c_str());
        if (!nodeType) throw cRuntimeError("Module Type \"%s\" not found", type.c_str());

        // TODO: this trashes the vectsize member of the cModule, although nobody seems to use it
        cModule* mod = nodeType->create(name.c_str(), parentmod, nodeVectorIndex, nodeVectorIndex);
        mod->finalizeParameters();
        if (displayString.length() > 0) {
            mod->getDisplayString().parse(displayString.c_str());
        }
        mod->buildInside();
        mod->scheduleStart(simTime() + updateInterval);

        preInitializeModule(mod, nodeId, position, road_id, speed, heading, signals);

        mod->callInitialize();
        hosts[nodeId] = mod;

        int nid = mod->findSubmodule("nic");
        kafkaConnection->setNameForMac(nid, nodeId);


        KDEBUG("ScenarioManager::addModule() added " << nodeId << " to hosts[] " << mod->getFullPath() << " id="<<mod->getId() <<" nic id="<< nid);


        updatedVIDs.push_back(nodeId);

        KDEBUG("size of updatedVIDS: " << updatedVIDs.size());
        for(auto s : updatedVIDs){
            std::cout << s <<", ";
        }
        std::cout <<std::endl;

        // post-initialize TraCIMobility
        auto mobilityModules = veins::getSubmodulesOfType<veins::TraCIMobility>(mod);
        for (auto mm : mobilityModules) {
            mm->changePosition();
        }



//        auto nics = veins::getSubmodulesOfType<veins::Nic80211p>(mod);
//        for (auto nic : nics) {
//            cout << nic->getID() << endl;
//        }

        // post-initialize TraCIMobility
//        auto app = veins::getSubmodulesOfType<DemoBaseApplLayer>(mod);
//        for (auto mm : app) {
//            cout << "KAfkaScenarioManager::addModule() added " << nodeId << " to hosts[] " << mod->getFullPath() << " id="<<mod->getId() << endl;
//
//        }

//        if (vehicleObstacleControl) {
//            std::vector<veins::AntennaPosition> initialAntennaPositions;
//            for (auto& caModule : veins::getSubmodulesOfType<veins::ChannelAccess>(mod, true)) {
//                initialAntennaPositions.push_back(caModule->getAntennaPosition());
//            }
//            ASSERT(mobilityModules.size() == 1);
//            auto mm = mobilityModules[0];
//            double offset = mm->getHostPositionOffset();
//            const veins::MobileHostObstacle* vo = vehicleObstacleControl->add(veins::MobileHostObstacle(initialAntennaPositions, mm, length, offset, width, height));
//            vehicleObstacles[mm] = vo;
//        }

        emit(traciModuleAddedSignal, mod);
    };

    virtual void updateModulePosition(cModule* mod, const veins::Coord& p, const std::string& edge, double speed, veins::Heading heading, veins::VehicleSignalSet signals){
        // update position in TraCIMobility
        auto mobilityModules = veins::getSubmodulesOfType<veins::TraCIMobility>(mod);
        for (auto mm : mobilityModules) {
            mm->nextPosition(p, edge, speed, heading, signals);
        }
    };


    void preInitializeModule(cModule* mod, const std::string& nodeId, const veins::Coord& position, const std::string& road_id, double speed, veins::Heading heading, veins::VehicleSignalSet signals)
    {
        // pre-initialize TraCIMobility
        auto mobilityModules = veins::getSubmodulesOfType<veins::TraCIMobility>(mod);
        for (auto mm : mobilityModules) {
            mm->preInitialize(nodeId, position, road_id, speed, heading);
        }
    };

    std::vector<std::string> getMapping(std::string el)
    {

        // search for string protection characters '
        char protection = '\'';
        size_t first = el.find(protection);
        size_t second;
        size_t eq;
        std::string type, value;
        std::vector<std::string> mapping;

        if (first == std::string::npos) {
            // there's no string protection, simply split by '='
            cStringTokenizer stk(el.c_str(), "=");
            mapping = stk.asVector();
        }
        else {
            // if there's string protection, we need to find a matching delimiter
            second = el.find(protection, first + 1);
            // ensure that a matching delimiter exists, and that it is at the end
            if (second == std::string::npos || second != el.size() - 1) throw cRuntimeError("invalid syntax for mapping \"%s\"", el.c_str());

            // take the value of the mapping as the text within the quotes
            value = el.substr(first + 1, second - first - 1);

            if (first == 0) {
                // if the string starts with a quote, there's only the value
                mapping.push_back(value);
            }
            else {
                // search for the equal sign
                eq = el.find('=');
                // this must be the character before the quote
                if (eq == std::string::npos || eq != first - 1) {
                    throw cRuntimeError("invalid syntax for mapping \"%s\"", el.c_str());
                }
                else {
                    type = el.substr(0, eq);
                }
                mapping.push_back(type);
                mapping.push_back(value);
            }
        }
        return mapping;
    };

    TypeMapping parseMappings(std::string parameter, std::string parameterName, bool allowEmpty)
    {

        /**
         * possible syntaxes
         *
         * "a"          : assign module type "a" to all nodes (for backward compatibility)
         * "a=b"        : assign module type "b" to vehicle type "a". the presence of any other vehicle type in the simulation will cause the simulation to stop
         * "a=b c=d"    : assign module type "b" to vehicle type "a" and "d" to "c". the presence of any other vehicle type in the simulation will cause the simulation to stop
         * "a=b c=d *=e": everything which is not of vehicle type "a" or "b", assign module type "e"
         * "a=b c=0"    : for vehicle type "c" no module should be instantiated
         * "a=b c=d *=0": everything which is not of vehicle type a or c should not be instantiated
         *
         * For display strings key-value pairs needs to be protected with single quotes, as they use an = sign as the type mappings. For example
         * *.manager.moduleDisplayString = "'i=block/process'"
         * *.manager.moduleDisplayString = "a='i=block/process' b='i=misc/sun'"
         *
         * moduleDisplayString can also be left empty:
         * *.manager.moduleDisplayString = ""
         */

        unsigned int i;
        TypeMapping map;

        // tokenizer to split into mappings ("a=b c=d", -> ["a=b", "c=d"])
        cStringTokenizer typesTz(parameter.c_str(), " ");
        // get all mappings
        std::vector<std::string> typeMappings = typesTz.asVector();
        // and check that there exists at least one
        if (typeMappings.size() == 0) {
            if (!allowEmpty)
                throw cRuntimeError("parameter \"%s\" is empty", parameterName.c_str());
            else
                return map;
        }

        // loop through all mappings
        for (i = 0; i < typeMappings.size(); i++) {

            // tokenizer to find the mapping from vehicle type to module type
            std::string typeMapping = typeMappings[i];

            std::vector<std::string> mapping = getMapping(typeMapping);

            if (mapping.size() == 1) {
                // we are where there is no actual assignment
                // "a": this is good
                // "a b=c": this is not
                if (typeMappings.size() != 1)
                    // stop simulation with an error
                    throw cRuntimeError("parameter \"%s\" includes multiple mappings, but \"%s\" is not mapped to any vehicle type", parameterName.c_str(), mapping[0].c_str());
                else
                    // all vehicle types should be instantiated with this module type
                    map["*"] = mapping[0];
            }
            else {

                // check that mapping is valid (a=b and not like a=b=c)
                if (mapping.size() != 2) throw cRuntimeError("invalid syntax for mapping \"%s\" for parameter \"%s\"", typeMapping.c_str(), parameterName.c_str());
                // check that the mapping does not already exist
                if (map.find(mapping[0]) != map.end()) throw cRuntimeError("duplicated mapping for vehicle type \"%s\" for parameter \"%s\"", mapping[0].c_str(), parameterName.c_str());

                // finally save the mapping
                map[mapping[0]] = mapping[1];
            }
        }

        return map;
    };

    void parseModuleTypes()
    {

        TypeMapping::iterator i;
        std::vector<std::string> typeKeys, nameKeys, displayStringKeys;

        std::string moduleTypes = par("moduleType").stdstringValue();
        std::string moduleNames = par("moduleName").stdstringValue();
        std::string moduleDisplayStrings = par("moduleDisplayString").stdstringValue();

        moduleType = parseMappings(moduleTypes, "moduleType", false);
        moduleName = parseMappings(moduleNames, "moduleName", false);
        moduleDisplayString = parseMappings(moduleDisplayStrings, "moduleDisplayString", true);

        // perform consistency check. for each vehicle type in moduleType there must be a vehicle type
        // in moduleName (and in moduleDisplayString if moduleDisplayString is not empty)

        // get all the keys
        for (i = moduleType.begin(); i != moduleType.end(); i++) typeKeys.push_back(i->first);
        for (i = moduleName.begin(); i != moduleName.end(); i++) nameKeys.push_back(i->first);
        for (i = moduleDisplayString.begin(); i != moduleDisplayString.end(); i++) displayStringKeys.push_back(i->first);

        // sort them (needed for intersection)
        std::sort(typeKeys.begin(), typeKeys.end());
        std::sort(nameKeys.begin(), nameKeys.end());
        std::sort(displayStringKeys.begin(), displayStringKeys.end());

        std::vector<std::string> intersection;

        // perform set intersection
        std::set_intersection(typeKeys.begin(), typeKeys.end(), nameKeys.begin(), nameKeys.end(), std::back_inserter(intersection));
        if (intersection.size() != typeKeys.size() || intersection.size() != nameKeys.size()) throw cRuntimeError("keys of mappings of moduleType and moduleName are not the same");

        if (displayStringKeys.size() == 0) return;

        intersection.clear();
        std::set_intersection(typeKeys.begin(), typeKeys.end(), displayStringKeys.begin(), displayStringKeys.end(), std::back_inserter(intersection));
        if (intersection.size() != displayStringKeys.size()) throw cRuntimeError("keys of mappings of moduleType and moduleName are not the same");
    };


    void deleteManagedModule(std::string nodeId);
};
}

