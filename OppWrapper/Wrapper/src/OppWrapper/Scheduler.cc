//=========================================================================
//  HLAdaceDS::Scheduler.CC - part of
//
//                  OMNeT++/OMNEST
//           Discrete System Simulation in C++
//
// Author: Levente Meszaros, 2009
//
//=========================================================================

/*--------------------------------------------------------------*
 Copyright (C) 2009-2015 OpenSim Ltd.

 This file is distributed WITHOUT ANY WARRANTY. See the file
 `license' for details on this and other legal matters.
 *--------------------------------------------------------------*/

#include "Scheduler.h"

#include <math.h>

Register_Class(daceDS::Scheduler);

daceDS::Scheduler* daceDS::Scheduler::inst = nullptr;
//Register_PerRunConfigOption(SCENARIOID, "scenarioID", CFG_STRING, "scenarioID-Foo", "The scenarioID.");

daceDS::Scheduler* daceDS::Scheduler::getInstance(){
    if(inst == nullptr){
        KERROR("KafkadaceDS::Scheduler needs to be called from OPP first" );
        exit(1);
    }
    return inst;
}



daceDS::Scheduler::Scheduler() throw ()
{


//    scenarioID =getEnvir()->getConfig()->getAsString(SCENARIOID, "fallbackscenario") ;


    std::cout << "daceDS::Scheduler()" << std::endl;
    inst = this;
}

daceDS::Scheduler::~Scheduler()
  throw ()
{
}

/*--------------------------------------------------------------*/

void daceDS::Scheduler::startRun()
{
    std::cout << "KafkadaceDS::Scheduler::startRun()" << std::endl;
    std::cout << "pwd=" << GetCurrentWorkingDir() << std::endl;
    KDEBUG("Starting...");
    if(!Config::getInstance()->readConfig(CONFIG_PROPERTIES)){
        KERROR ("Config not found under "<< CONFIG_PROPERTIES << " ! Exiting...");
        exit(1);
    }
    KDEBUG ("Config::getInstance()->get(\"schemaRegistry\")=" <<Config::getInstance()->get("schemaRegistry"));
    cModule *sys = getSimulation()->getSystemModule();
    cModule *man = sys->getModuleByPath("daceDSBaseScenario.kmanager");

    scenarioID = man->par("ScenarioID").stdstringValue();
    simulatorID = man->par("SimulatorID").stdstringValue();
    std::string topic = "orchestration.simulation."+scenarioID+".sync";

    daceDS::Config::getInstance()->setScenarioID(scenarioID);
    daceDS::Config::getInstance()->setSimulatorID(simulatorID);
    std::string host = Config::getInstance()->get("kafkaBroker");

    //init kafka
    //first, create directory: we might receive resources
    //createDirs();

    //then we fetch the scenario definition

    //provision
    daceDS::OppWrapper::createInstance(scenarioID,simulatorID);
    auto provision = std::make_shared<OppProvisionImpl>(daceDS::OppWrapper::getInstance());
    std::shared_ptr<ProvisionHandlerCommunication11p> phdl = std::make_shared<ProvisionHandlerCommunication11p>(provision);
    KafkaConsumer scenarioConsumer(phdl);   //we need this only once, is deleted afterwards
    std::string scenarioTopic = Config::getInstance()->getProvisionBaseTopic(TOPIC_SCENARIO);
    KDEBUG("Subscribing to " << scenarioTopic);

    std::vector<std::string> scenarioTopics;
    scenarioTopics.push_back(scenarioTopic);
    scenarioConsumer.subscribe(host, scenarioTopics, Constants::STR_SCENARIO_CONSUMER, "");

    // statusMsg("(waiting for scenario description...)");
    auto sce = provision->waitForScenario();
    auto sim = provision->getSim();
    scenarioConsumer.stop();


    syncedParticipants = sce->execution.syncedParticipants;
    getSimulation()->setSimulationTimeLimit(sce->simulationEnd);


    KINFO("topic=" << topic );
    KINFO("syncedParticipants=" << syncedParticipants );
    KINFO("timesyncID=" << scenarioID+"_"+simulatorID+"_timeSync" );

    timeSync = std::make_shared<TimeSync>(topic, syncedParticipants);
    KINFO("init" );
    timeSync->init<KafkaConsumer,KafkaProducer>();
    KINFO("prepare" );
    timeSync->prepare();
    KINFO("joinTiming" );
    timeSync->joinTiming();
    KINFO("joined Timing" );
}

void daceDS::Scheduler::endRun()
{
    //todo: what else?
    timeSync->leaveTiming();
}

cEvent *daceDS::Scheduler::guessNextEvent()
{
    return sim->getFES()->peekFirst();
}

cEvent *daceDS::Scheduler::takeNextEvent()
{

//    std::cout << "KafkadaceDS::Scheduler::takeNextEvent" << std::endl;
    cEvent *event = nullptr;

    long maxstepMS = 1000;
    double minStepMS = 10.0;
    while (true) {
        // stop simulation upon user request
        if (getEnvir()->idle())
            return nullptr;

        long timeInMS = timeSync->getLBTSInMS();
        // KINFO("timeInMS " << timeInMS );

        // we might be here after processing a previously returned message
        // or if the user stopped the simulation during waiting for a time advance
//        if (requestTimeAdvanceCompleted) {
            event = sim->getFES()->peekFirst();

            KDEBUG ("FES length: " << sim->getFES()->getLength() );

            long nextMaxStepMS = maxstepMS - (timeInMS % maxstepMS);
            if (event) {
                // check if we are allowed to process this event

                if (event->getArrivalTime().inUnit(SimTimeUnit::SIMTIME_MS) <= timeInMS){
                    return sim->getFES()->removeFirst();
                }
                else{
                    // request time advance to be able to process this event
                    KDEBUG(" current time in ms=" << timeInMS );
                    KDEBUG(" event->getArrivalTime()=" << event->getArrivalTime().inUnit(SimTimeUnit::SIMTIME_MS) );

                    long stepInMS = event->getArrivalTime().inUnit(SimTimeUnit::SIMTIME_MS) - timeInMS;
                    KDEBUG(" raw stepInMS =" << stepInMS );

                    //get next minStep
                    long ceiledStep = ceil(stepInMS / minStepMS) * minStepMS;
                    long stepInMs = min(nextMaxStepMS,ceiledStep);
                    KDEBUG(" need additional ms=" << stepInMS );
                    KDEBUG(" minStepMS=" << minStepMS );
                    KDEBUG(" --> ceiledStepMS=" << ceiledStep );
                    KDEBUG(" maxStepMS=" << maxstepMS );
                    KDEBUG(" --> nextMaxStepMS=" << nextMaxStepMS );
                    KDEBUG(" --> timeAdvance of " << stepInMs );
                    timeSync->timeAdvance(stepInMs);
                    interactionHandler->processBuffer(timeSync->getLBTSInMS(),0);
                    provisionHandler->processBuffer(timeSync->getLBTSInMS(),0);
                }
            }
            else{
                KDEBUG(" maxstep" << nextMaxStepMS );
                timeSync->timeAdvance(nextMaxStepMS);

                interactionHandler->processBuffer(timeSync->getLBTSInMS(),0);
                provisionHandler->processBuffer(timeSync->getLBTSInMS(),0);
            }
    }
}


