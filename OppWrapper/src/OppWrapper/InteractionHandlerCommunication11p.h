#pragma once

#include "/home/mohamed/Desktop/DaceDS/DaceDS4energy-main/CppBaseWrapper/src/api/Provision.h"
#include "communication/InteractionHandler.h"
#include "communication/AvroHelper.h"
#include "OppInteractionImpl.h"  // ✅ Ensure OppInteractionImpl is included

/*
Each consumer uses a single messageHandler implementation to process incoming messages.
Used to implement handlers for orchestration, interaction, and provision channel.
*/

namespace daceDS {
class OppWrapper;

class InteractionHandlerCommunication11p : public InteractionHandler {
   protected:
    std::shared_ptr<OppInteractionImpl> api;  // ✅ Use full namespace

   public:
    InteractionHandlerCommunication11p(std::shared_ptr<daceDS::OppInteractionImpl> i, std::shared_ptr<Producer> p)
        : InteractionHandler(p), api(i) {}  // ✅ Ensure constructor matches correct parameters

    virtual ~InteractionHandlerCommunication11p(){};

    bool handle(ConsumedMessage* msg);
};
}

