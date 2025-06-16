#include "../OppWrapper/TriggerMsgApp.h"

#include <iostream>

Define_Module(TriggerMsgApp);

void TriggerMsgApp::initialize(int stage)
{

    veins::BaseApplLayer::initialize(stage);

//    std::cout << "TriggerMsgApp::initialize()" << std::endl;
    if (stage == 0) {

        mac = veins::FindModule<veins::DemoBaseApplLayerToMac1609_4Interface*>::findSubModule(getParentModule());
        ASSERT(mac);

        // read parameters
        headerLength = par("headerLength");
        sendBeacons = par("sendBeacons").boolValue();
        beaconLengthBits = par("beaconLengthBits");
        beaconUserPriority = par("beaconUserPriority");
        beaconInterval = par("beaconInterval");
        dataLengthBits = par("dataLengthBits");
        dataOnSch = par("dataOnSch").boolValue();
        dataUserPriority = par("dataUserPriority");


        sendBeaconEvt = new cMessage("beacon evt", SEND_BEACON_EVT);

        findHost()->subscribe(veins::BaseMobility::mobilityStateChangedSignal, this);

        generatedWSMs = 0;
        receivedWSMs = 0;
        generatedRadioMessages = 0;
        receivedRadioMessages = 0;
    }
    else if (stage == 1) {

        // store MAC address for quick access
        myId = mac->getMACAddress();

        // simulate asynchronous channel access

        if (dataOnSch == true && !mac->isChannelSwitchingActive()) {
            dataOnSch = false;
            EV_ERROR << "App wants to send data on SCH but MAC doesn't use any SCH. Sending all data on CCH" << std::endl;
        }
        simtime_t firstBeacon = simTime();

        if (par("avoidBeaconSynchronization").boolValue() == true) {

            simtime_t randomOffset = dblrand() * beaconInterval;
            firstBeacon = simTime() + randomOffset;

            if (mac->isChannelSwitchingActive() == true) {
                if (beaconInterval.raw() % (mac->getSwitchingInterval().raw() * 2)) {
                    EV_ERROR << "The beacon interval (" << beaconInterval << ") is smaller than or not a multiple of  one synchronization interval (" << 2 * mac->getSwitchingInterval() << "). This means that beacons are generated during SCH intervals" << std::endl;
                }
                firstBeacon = computeAsynchronousSendingTime(beaconInterval, veins::ChannelType::control);
            }

            if (sendBeacons) {
                scheduleAt(firstBeacon, sendBeaconEvt);
            }
        }


        connection = daceDS::OppWrapper::getInstance();
    }
}

void TriggerMsgApp::finish()
{
    recordScalar("generatedRadioMessages", generatedRadioMessages);
    recordScalar("receivedRadioMessages", receivedRadioMessages);

    recordScalar("generatedWSMs", generatedWSMs);
    recordScalar("receivedWSMs", receivedWSMs);
}

TriggerMsgApp::~TriggerMsgApp()
{
    cancelAndDelete(sendBeaconEvt);
    findHost()->unsubscribe(veins::BaseMobility::mobilityStateChangedSignal, this);
}

void TriggerMsgApp::populateRadioMessage(veins::RadioMessage* rmsg, veins::LAddress::L2Type rcvId, int serial)
{
    rmsg->setRecipientAddress(rcvId);
    rmsg->setSender(std::to_string(myId).c_str());
    rmsg->setBitLength(headerLength);
    rmsg->setPsid(-1);
    rmsg->setChannelNumber(static_cast<int>(veins::Channel::cch));
    rmsg->addBitLength(beaconLengthBits);
    rmsg->setUserPriority(beaconUserPriority);
    rmsg->setChannelNumber(static_cast<int>(veins::Channel::cch));
    rmsg->addBitLength(dataLengthBits);
    rmsg->setUserPriority(dataUserPriority);

}

void TriggerMsgApp::onRadioMessage(veins::RadioMessage* rmsg){

//    std::cout << std::to_string(myId) << ": received RadioMessage, translating to radiomsg and forwarding to kafka" << std::endl;

    int id = atoi(rmsg->getSender());
    daceDS::datamodel::RadioMsg radioMsg;
    radioMsg.sender = daceDS::OppWrapper::getInstance()->getNameForMac(id);
    radioMsg.sendTime = rmsg->getCreationTime().inUnit(SimTimeUnit::SIMTIME_US);
    radioMsg.receiver = daceDS::OppWrapper::getInstance()->getNameForMac(myId);
    radioMsg.receiveTime = simTime().inUnit(SimTimeUnit::SIMTIME_US);
    radioMsg.data["ByteLength"] = std::to_string(rmsg->getByteLength());
    radioMsg.data["ChannelNumber"] = std::to_string(rmsg->getChannelNumber());

    for (auto const& x : rmsg->getData()){
        radioMsg.data[x.first] = x.second;
    }

    daceDS::OppWrapper::getInstance()->notifyMsgReceived(radioMsg);

    KDEBUG (std::to_string(myId) << ": received RadioMessage, translating to radiomsg and forwarding to kafka --> done");
}


void TriggerMsgApp::handleSelfMsg(cMessage* msg)
{
    switch (msg->getKind()) {
    case SEND_BEACON_EVT: {
        veins::RadioMessage* rmsg = new veins::RadioMessage();
        populateRadioMessage(rmsg, -1, 0);
        veins::TraCICoord p = daceDS::OppWrapper::getInstance()->omnet2traci(veins::Coord(curPosition.x, curPosition.y));
        Datamap d;
        d["x"]=std::to_string(p.x);
        d["y"]=std::to_string(p.y);
        rmsg->setData(d);
        // std::cout<<"SEND_BEACON_EVT"<< std::endl;
        sendDown(rmsg);
        scheduleAt(simTime() + beaconInterval, sendBeaconEvt);
        break;
    }
    default: {
        if (msg) EV_WARN << "APP: Error: Got Self Message of unknown kind! Name: " << msg->getName() << endl;
        break;
    }
    }
}


void TriggerMsgApp::sendMsg(daceDS::datamodel::RadioMsg& msg){
    std::cout << "transmitting" << std::endl;

    veins::RadioMessage* rmsg = new veins::RadioMessage();
    populateRadioMessage(rmsg, -1, 0);

    rmsg->setData(msg.data);

    take(rmsg); //important, called from traciscenariomanager. with take gets owned by this module.
    sendDown(rmsg);

}

void TriggerMsgApp::sendDown(cMessage* msg)
{

    daceDS::datamodel::RadioMsg radioMsg;
    radioMsg.sender = daceDS::OppWrapper::getInstance()->getNameForMac(myId);
    radioMsg.data = ((veins::RadioMessage*)msg)->getData();
    radioMsg.sendTime = ((veins::RadioMessage*)msg)->getCreationTime().inUnit(SimTimeUnit::SIMTIME_US);
    radioMsg.data["ByteLength"] = std::to_string(((veins::RadioMessage*)msg)->getByteLength());
    radioMsg.data["ChannelNumber"] = std::to_string(((veins::RadioMessage*)msg)->getChannelNumber());
    daceDS::OppWrapper::getInstance()->notifyMsgSent(radioMsg);

    checkAndTrackPacket(msg);
    BaseApplLayer::sendDown(msg);
}

void TriggerMsgApp::checkAndTrackPacket(cMessage* msg)
{
    if (dynamic_cast<veins::RadioMessage*>(msg)) {
        EV_TRACE << "sending down a RadioMessage" << std::endl;
        generatedRadioMessages++;
    }
    else if (dynamic_cast<veins::BaseFrame1609_4*>(msg)) {
        EV_TRACE << "sending down a wsm" << std::endl;
        generatedWSMs++;
    }
}

void TriggerMsgApp::handleLowerMsg(cMessage* msg)
{

    // std::cout << myId << ": handleLowerMsg " << simTime().dbl() << std::endl;

    veins::BaseFrame1609_4* wsm = dynamic_cast<veins::BaseFrame1609_4*>(msg);
    ASSERT(wsm);

    if (veins::RadioMessage* wsa = dynamic_cast<veins::RadioMessage*>(wsm)) {
        receivedRadioMessages++;
        onRadioMessage(wsa);
    }
    else {
        receivedWSMs++;
    }

    delete (msg);
}

simtime_t TriggerMsgApp::computeAsynchronousSendingTime(simtime_t interval, veins::ChannelType chan)
{

    /*
     * avoid that periodic messages for one channel type are scheduled in the other channel interval
     * when alternate access is enabled in the MAC
     */

    simtime_t randomOffset = dblrand() * interval;
    simtime_t firstEvent;
    simtime_t switchingInterval = mac->getSwitchingInterval(); // usually 0.050s
    simtime_t nextCCH;

    /*
     * start event earliest in next CCH (or SCH) interval. For alignment, first find the next CCH interval
     * To find out next CCH, go back to start of current interval and add two or one intervals
     * depending on type of current interval
     */

    if (mac->isCurrentChannelCCH()) {
        nextCCH = simTime() - SimTime().setRaw(simTime().raw() % switchingInterval.raw()) + switchingInterval * 2;
    }
    else {
        nextCCH = simTime() - SimTime().setRaw(simTime().raw() % switchingInterval.raw()) + switchingInterval;
    }

    firstEvent = nextCCH + randomOffset;

    // check if firstEvent lies within the correct interval and, if not, move to previous interval

    if (firstEvent.raw() % (2 * switchingInterval.raw()) > switchingInterval.raw()) {
        // firstEvent is within a sch interval
        if (chan == veins::ChannelType::control) firstEvent -= switchingInterval;
    }
    else {
        // firstEvent is within a cch interval, so adjust for SCH messages
        if (chan == veins::ChannelType::service) firstEvent += switchingInterval;
    }

    return firstEvent;
}

void TriggerMsgApp::receiveSignal(cComponent* source, simsignal_t signalID, cObject* obj, cObject* details)
{
    Enter_Method_Silent();
    if (signalID == veins::BaseMobility::mobilityStateChangedSignal) {
        handlePositionUpdate(obj);
    }
}

void TriggerMsgApp::handlePositionUpdate(cObject* obj)
{
    veins::ChannelMobilityPtrType const mobility = check_and_cast<veins::ChannelMobilityPtrType>(obj);
    curPosition = mobility->getPositionAt(simTime());
    curSpeed = mobility->getCurrentSpeed();

    // std::cout << myId << ", new pos: " << curPosition.x << "," << curPosition.y << ", speed: " << curSpeed.length() << std::endl;
}
