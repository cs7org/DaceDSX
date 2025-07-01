/*******************************************************************************
 * Copyright 2021 Moritz Gütlein
 * 
 * Licensed under the Apache License, Version 2.0 (the "License"); you may not
 * use this file except in compliance with the License.  You may obtain a copy
 * of the License at
 * 
 *   http://www.apache.org/licenses/LICENSE-2.0
 * 
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
 * License for the specific language governing permissions and limitations under
 * the License.
 ******************************************************************************/

#include "OppInteractionImpl.h"
#include "OppWrapper.h"  // ✅ Ensure OppWrapper is included

using namespace daceDS;

void OppInteractionImpl::handleInteractionPositionUpdate(int64_t t, int64_t st, daceDS::datamodel::InteractionMsg msg) {
    auto inp = msg.Input;

    if (inp.find("vehicleID") == inp.end() || inp.find("x") == inp.end() || inp.find("y") == inp.end() || inp.find("z") == inp.end()) {
        KERROR("Missing required fields in InteractionMsg Input");
        return;
    }

    std::string vid = inp["vehicleID"];
    double x = std::stod(inp["x"]);
    double y = std::stod(inp["y"]);
    double z = std::stod(inp["z"]);

    auto oppWrapper = std::dynamic_pointer_cast<OppWrapper>(wrapper);
    if (oppWrapper) {
        oppWrapper->handlePositionUpdate(t, st, vid, x, y, z);
    } else {
        KERROR("Failed to cast SimulationWrapper to OppWrapper in handleInteractionPositionUpdate");
    }
}


void daceDS::OppInteractionImpl::handleInteractionSendRadioMsg(daceDS::datamodel::RadioMsg msg){
    (std::dynamic_pointer_cast<OppWrapper>(wrapper))->handleTopicSendRadioMsg(msg);
}


