#pragma once
#include <exception>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <vector>

#include "api/Interaction.h"
#include "main/SimulationWrapper.h"
#include "util/Config.h"
#include "util/Defines.h"
#include "datamodel/RadioMsg.hh"
namespace daceDS {

// ✅ Forward declare OppWrapper instead of including "OppWrapper.h"
class OppWrapper;

class OppInteractionImpl : public Interaction {
   public:
    OppInteractionImpl(std::shared_ptr<SimulationWrapper> w) : Interaction() {
        wrapper = w;
    };
    virtual ~OppInteractionImpl(){};

    std::shared_ptr<SimulationWrapper> wrapper;

    void handleInteractionPositionUpdate(int64_t, int64_t, daceDS::datamodel::InteractionMsg msg);
    void handleInteractionSendRadioMsg(daceDS::datamodel::RadioMsg msg);
};
}  // namespace daceDS

