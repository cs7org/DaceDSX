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


#include "ScenarioManager.h"

#include "TriggerMsgApp.h"


Define_Module(daceDS::ScenarioManager);

const simsignal_t daceDS::ScenarioManager::traciInitializedSignal = registerSignal("org_car2x_veins_modules_mobility_traciInitialized");
const simsignal_t daceDS::ScenarioManager::traciModuleAddedSignal = registerSignal("org_car2x_veins_modules_mobility_traciModuleAdded");
const simsignal_t daceDS::ScenarioManager::traciModuleRemovedSignal = registerSignal("org_car2x_veins_modules_mobility_traciModuleRemoved");
const simsignal_t daceDS::ScenarioManager::traciTimestepBeginSignal = registerSignal("org_car2x_veins_modules_mobility_traciTimestepBegin");
const simsignal_t daceDS::ScenarioManager::traciTimestepEndSignal = registerSignal("org_car2x_veins_modules_mobility_traciTimestepEnd");

daceDS::ScenarioManager::ScenarioManager(){

    std::cout << "KafkadaceDS::ScenarioManager()" << std::endl;
}

daceDS::ScenarioManager::~ScenarioManager()
{
    if (kafkaConnection) {
        kafkaConnection->close();
    }
}

void daceDS::ScenarioManager::initialize(int stage)
{
    std::cout << "KafkadaceDS::ScenarioManager::initialize" << std::endl;
    if (stage !=0) {
        return;
    }
    scenarioID = par("ScenarioID").stdstringValue();//.intValue());
    simulatorID =par("SimulatorID").stdstringValue();//.intValue());
    std::cout << "simulatorID=" << simulatorID << std::endl;
    std::cout << "scenarioIDstr=" << scenarioID << std::endl;
    EV_DEBUG << "initialized TraCIdaceDS::ScenarioManagerFoo" << endl;

    kafkaConnection = OppWrapper::getInstance();

    connectAt = par("connectAt");
    firstStepAt = par("firstStepAt");
    updateInterval = par("updateInterval");
    if (firstStepAt == -1) firstStepAt = connectAt + updateInterval;
    nextNodeVectorIndex = 0;
    hosts.clear();
    subscribedVehicles.clear();

    ASSERT(firstStepAt > connectAt);
    connectAndStartTrigger = new cMessage("connect");
    scheduleAt(0, connectAndStartTrigger);
    executeOneTimestepTrigger = new cMessage("step");
    scheduleAt(firstStepAt, executeOneTimestepTrigger);

    //for vtypes
    parseModuleTypes();
}

void daceDS::ScenarioManager::init()
{
    std::cout << "daceDS::ScenarioManager::init" << std::endl;
    
    // values for PoC
    //todo: query and set road network boundaries
    int margin = 25;
    veins::TraCICoord nb1(-10000.0,-10000.0);
    veins::TraCICoord nb2(10000,10000);
    std::pair<veins::TraCICoord, veins::TraCICoord> networkBoundaries(nb1,nb2);
    kafkaConnection->setNetbounds(nb1, nb2, margin);

//    if (world != nullptr && ((kafkaConnection->traci2omnet(networkBoundaries.second).x > world->getPgs()->x) || (kafkaConnection->traci2omnet(networkBoundaries.first).y > world->getPgs()->y))) {
//        cout << "WARNING: Playground size (" << world->getPgs()->x << ", " << world->getPgs()->y << ") might be too small for vehicle at network bounds (" << kafkaConnection->traci2omnet(networkBoundaries.second).x << ", " << kafkaConnection->traci2omnet(networkBoundaries.first).y << ")" << endl;
//    }
    traciInitialized = true;
    emit(traciInitializedSignal, true);
}

void daceDS::ScenarioManager::handleMessage(cMessage* msg)
{
    if (msg->isSelfMessage()) {
        handleSelfMsg(msg);
        return;
    }
    throw cRuntimeError("ScenarioManager doesn't handle messages from other modules");
}

void daceDS::ScenarioManager::handleSelfMsg(cMessage* msg)
{
//    std::cout << "KafkadaceDS::ScenarioManager::handleSelfMsg" << std::endl;
    if (msg == connectAndStartTrigger) {
        std::cout << "KafkadaceDS::ScenarioManager::connectAndStartTrigger" << std::endl;
        kafkaConnection->init();
        init();
        return;
    }
    if (msg == executeOneTimestepTrigger) {
    //    std::cout << "KafkadaceDS::ScenarioManager::executeOneTimestepTrigger" << std::endl;
        executeOneTimestep();
        return;
    }
    throw cRuntimeError("ScenarioManager received unknown self-message");
}


void daceDS::ScenarioManager::executeOneTimestep()
{
    if (isConnected()) {
        //inject received position updates
        processSubcriptionResult();

        //trigger received message transmissions
        processSendMsgRequests();

    }

    scheduleAt(simTime() + updateInterval, executeOneTimestepTrigger);
}


//called for provision updates
void daceDS::ScenarioManager::processVehicleSubscription(daceDS::datamodel::Micro& micro)
{

    KDEBUG ("daceDS::ScenarioManager::processVehicleSubscription()");
    std::string objectId = micro.vehicleID;
    bool isSubscribed = (subscribedVehicles.find(objectId) != subscribedVehicles.end());
    double px = micro.position.x;
    double py = micro.position.y;
    std::string edge = micro.edge;
    double speed = micro.speed;
    double angle_traci = micro.angle;
    int signals = 0;
    double length = 5.00; //todo get from micro.type
    double height = 2.00; //todo
    double width = 2.00; //todo

    veins::Coord p = kafkaConnection->traci2omnet(veins::TraCICoord(px, py));
    if ((p.x < 0) || (p.y < 0)) throw cRuntimeError("received bad node position (%.2f, %.2f), translated to (%.2f, %.2f)", px, py, p.x, p.y);
    veins::Heading heading = kafkaConnection->traci2omnetHeading(angle_traci);

    cModule* mod = getManagedModule(objectId);

    if (!mod) {
        // no such module - need to create
        std::string vType = micro.type;
        std::string mType, mName, mDisplayString;
        TypeMapping::iterator iType, iName, iDisplayString;

        TypeMapping::iterator i;
        iType = moduleType.find(vType);
        if (iType == moduleType.end()) {
            iType = moduleType.find("*");
            if (iType == moduleType.end()) throw cRuntimeError("cannot find a module type for vehicle type \"%s\"", vType.c_str());
        }
        mType = iType->second;
        // search for module name
        iName = moduleName.find(vType);
        if (iName == moduleName.end()) {
            iName = moduleName.find(std::string("*"));
            if (iName == moduleName.end()) throw cRuntimeError("cannot find a module name for vehicle type \"%s\"", vType.c_str());
        }
        mName = iName->second;
        if (moduleDisplayString.size() != 0) {
            iDisplayString = moduleDisplayString.find(vType);
            if (iDisplayString == moduleDisplayString.end()) {
                iDisplayString = moduleDisplayString.find("*");
                if (iDisplayString == moduleDisplayString.end()) throw cRuntimeError("cannot find a module display string for vehicle type \"%s\"", vType.c_str());
            }
            mDisplayString = iDisplayString->second;
        }
        else {
            mDisplayString = "";
        }

        if (mType != "0") {
            addModule(objectId, mType, mName, mDisplayString, p, edge, speed, heading, veins::VehicleSignalSet(signals), length, height, width);
            EV_DEBUG << "Added vehicle #" << objectId << endl;
            KDEBUG ("Added vehicle " << objectId);
        }

    }
    else {
        // module existed - update position
        KDEBUG ("module " << objectId << " moving to " << px << "," << py);
        EV_DEBUG << "module " << objectId << " moving to " << px << "," << py << endl;
        updateModulePosition(mod, p, edge, speed, heading, veins::VehicleSignalSet(signals));
    }
}

void daceDS::ScenarioManager::processSubcriptionResult()
{
    
    std::vector<std::string> toDelete;
    std::string vs="";
    for(auto s : updatedVIDs){
        vs +=s+",";
    }
    KDEBUG("updated "<< updatedVIDs.size()<< " vehicles in last step ("<<vs<<")");
    for(std::map<std::string,cModule*>::iterator it = hosts.begin(); it != hosts.end(); ++it) {
        std::string vid = it->first;

        if(std::find(updatedVIDs.begin(), updatedVIDs.end(), vid)==updatedVIDs.end()){
                std::cout << "Vehicle " << it->first << " was not updated, deleting... "<< std::endl;
                toDelete.push_back(vid);
        }
    }
    for(auto vid : toDelete){
        try{
            deleteManagedModule(vid);
        } catch(std::exception &e){
            KERROR("failed to delete vehicle "<< vid << ": " << e.what());
        }
    }
    updatedVIDs.clear();


    ///////// pre cppbase buffered version
     long msec = ((long)simTime().dbl()-2) * 1000 ;
     KDEBUG("subscription sets: " << kafkaConnection->unreadSubscribtions.size());
     KDEBUG("looking for my time: " << msec);
     if(kafkaConnection->unreadSubscribtions.count(msec) > 0){
         for(daceDS::datamodel::Micro vehicle : kafkaConnection->unreadSubscribtions[msec]){
             if(std::find(toDelete.begin(), toDelete.end(), vehicle.vehicleID)!=toDelete.end()){

                     KERROR("recently deleted vehicle "<<  vehicle.vehicleID);
             }
             else{
                     processVehicleSubscription(vehicle);
                     updatedVIDs.push_back(vehicle.vehicleID);
             }
         }
         kafkaConnection->unreadSubscribtions[msec].clear();
         kafkaConnection->unreadSubscribtions.erase(msec);
     }
     else{
         KDEBUG("did not find anything, only got:");
         for (auto const& pair: kafkaConnection->unreadSubscribtions) {
             KDEBUG ( "{" << pair.first << ": " << pair.second.size() << " entries}");
         }
     }

}

//called for provision updates
void daceDS::ScenarioManager::processSendMsgRequest(daceDS::datamodel::RadioMsg& msg)
{
    std::string objectId = msg.sender;

    cModule* mod = getManagedModule(objectId);
    if (!mod) {
        KINFO("sender=" <<objectId << " is not found");
        KDEBUG("available nodes: ");
        string bla;
        for (auto entry : hosts){
            bla = entry.first;
            KDEBUG (entry.first);
        }
        return;
    }

    std::vector<TriggerMsgApp*> apps = veins::getSubmodulesOfType<TriggerMsgApp>(mod, true);
    if (apps.size() ==0) {
        KDEBUG ("TriggerMsgApp is not found for node=" << objectId);
        return;
    }

    TriggerMsgApp* app = apps[0];
    KINFO("app->sendMsg(msg)");
    app->sendMsg(msg);
}

void daceDS::ScenarioManager::processSendMsgRequests()
{
//    KINFO ("number of unreadsendMsgRequests=" << kafkaConnection->unreadsendMsgRequests.size());
    for(daceDS::datamodel::RadioMsg msg : kafkaConnection->unreadsendMsgRequests){
        processSendMsgRequest(msg);
    }
    kafkaConnection->unreadsendMsgRequests.clear();
}

void daceDS::ScenarioManager::deleteManagedModule(std::string nodeId)
{
    if (subscribedVehicles.find(nodeId) != subscribedVehicles.end()) {
        subscribedVehicles.erase(nodeId);                }

    // check if this object has been deleted already (e.g. because it was outside the ROI)
    cModule* mod = getManagedModule(nodeId);

    if (!mod) throw cRuntimeError("no vehicle with Id \"%s\" found", nodeId.c_str());
    if (mod){
        emit(traciModuleRemovedSignal, mod);
        auto cas = veins::getSubmodulesOfType<veins::ChannelAccess>(mod, true);
        KDEBUG("cas size "<<cas.size());
        for (auto ca : cas) {
            cModule* nic = ca->getParentModule();
            auto connectionManager = veins::ChannelAccess::getConnectionManager(nic);
            connectionManager->unregisterNic(nic);
        }
        mod->callFinish();
        mod->deleteModule();

        KDEBUG("deleted module "<<nodeId);
        hosts.erase(nodeId);
    } 

    if (unEquippedHosts.find(nodeId) != unEquippedHosts.end()) {
        unEquippedHosts.erase(nodeId);
    }
    
}



