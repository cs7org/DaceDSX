#ifndef KAFKASCHEDULER
#define KAFKASCHEDULER

#include <memory>
#include <omnetpp.h>
#include "logic/TimeSync.h"
#include "util/log.h"
#include "ProvisionHandlerCommunication11p.h"
#include "InteractionHandlerCommunication11p.h"
#include "OppProvisionImpl.h"
#include "communication/kafka/KafkaConsumer.h"
#include "communication/kafka/KafkaProducer.h"

using namespace std;
using namespace omnetpp;

namespace daceDS {
class ProvisionHandlerCommunication11p;
class InteractionHandlerCommunication11p;
class OppProvisionImpl;

class Scheduler : public cScheduler {
    bool requestTimeAdvanceCompleted = false;
    std::shared_ptr<TimeSync> timeSync;
    std::shared_ptr<ProvisionHandlerCommunication11p> provisionHandler;
    std::shared_ptr<InteractionHandlerCommunication11p> interactionHandler;
    std::string scenarioID;
    std::string simulatorID;
    int syncedParticipants;
    static Scheduler* inst;

  protected:
    // notifies the HLA RTI that the simulation time can be advanced to the given value
//    void requestTimeAdvance(SimTime simulationTime);
    // waits until the given flag becomes non zero
//    void waitUntil(const char *name, bool &flag);

  public:
    Scheduler() throw ();
    ~Scheduler() throw();

//    void setSimulation(cSimulation *_sim) override;

    /**
     * Creates the HLA federation execution, initializes the RTI ambassador.
     * Switches the RTI to time constrained and time regulation mode and synchronizes with other federates.
     */
    void startRun();
    /*
     * Destroys the HLA federation execution.
     */
    void endRun();

    void registerProvisionHandler(std::shared_ptr<ProvisionHandlerCommunication11p> p){
        provisionHandler = p;
    }; 
    
    void registerInteractionHandler(std::shared_ptr<InteractionHandlerCommunication11p> i){
        interactionHandler = i;
    };

    /**
     * Return the likely next event in the simulation. This method is for UI
     * purposes, it does not play any role in the simulation.
     */
    cEvent *guessNextEvent();

    /**
     * This method returns the next message to be handled within the OMNeT++ simulation. It checks
     * if the first message in the FES has a smaller or equal arrival time than the last simulation
     * time granted by the RTI. If so, it returns that message, otherwise it requests the RTI to advance
     * the simulation time to the arrival time. If there is no message in the FES, then a time advance
     * is requested without a limit. The user interface is continuously checked to see if the user
     * wants to pause the simulation.
     */
    cEvent *takeNextEvent();

    void putBackEvent(cEvent *event){};

    std::shared_ptr<TimeSync> getTimeSync(){
        return timeSync;
    }
    static Scheduler* getInstance();
};
}

#endif
