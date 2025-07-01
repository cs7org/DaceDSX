//
// Copyright (C) 2016 David Eckhoff <david.eckhoff@fau.de>
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
#include "veins/veins.h"
#include "veins/modules/messages/RadioMessage_m.h"
#include "veins/base/modules/BaseApplLayer.h"
#include "veins/base/connectionManager/ChannelAccess.h"
#include "veins/modules/mac/ieee80211p/DemoBaseApplLayerToMac1609_4Interface.h"

#include "datamodel/RadioMsg.hh"

using namespace omnetpp;

class TriggerMsgApp : public veins::BaseApplLayer {
public:
    ~TriggerMsgApp() override;
    void initialize(int stage);
    void finish();

    void sendMsg(daceDS::datamodel::RadioMsg& msg);
    std::shared_ptr<daceDS::OppWrapper> connection;

    enum MessageKinds {
        SEND_BEACON_EVT
    };

protected:
    void onRadioMessage(veins::RadioMessage* rmsg);
    void populateRadioMessage(veins::RadioMessage* rmsg, veins::LAddress::L2Type rcvId, int serial);

    void handleLowerMsg(cMessage* msg) override;
    void handleSelfMsg(cMessage* msg) override;

    /** @brief this function is called every time the vehicle receives a position update signal */
    simtime_t computeAsynchronousSendingTime(simtime_t interval, veins::ChannelType chantype);
    void sendDown(cMessage* msg);
    void checkAndTrackPacket(cMessage* msg);

    void receiveSignal(cComponent* source, simsignal_t signalID, cObject* obj, cObject* details);
    void handlePositionUpdate(cObject* obj);

    veins::DemoBaseApplLayerToMac1609_4Interface* mac;


    /* BSM (beacon) settings */
    uint32_t beaconLengthBits;
    uint32_t beaconUserPriority;
    simtime_t beaconInterval;
    bool sendBeacons;

    /* WSM (data) settings */
    uint32_t dataLengthBits;
    uint32_t dataUserPriority;
    bool dataOnSch;

    /* state of the vehicle */
    veins::Coord curPosition;
    veins::Coord curSpeed;
    veins::LAddress::L2Type myId = 0;
    int mySCH;

    /* stats */
    uint32_t generatedWSMs;
    uint32_t generatedRadioMessages;
    uint32_t receivedWSMs;
    uint32_t receivedRadioMessages;

    cMessage* sendBeaconEvt;


};




