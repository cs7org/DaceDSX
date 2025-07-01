#include "InteractionHandlerCommunication11p.h"

#include <cstddef>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

using namespace daceDS;

bool InteractionHandlerCommunication11p::handle(ConsumedMessage* msg) {
    std::string topic = msg->topic;
    KINFO("Got message in topic = " << topic);

    if (topic.find("interaction") != std::string::npos) {
        daceDS::datamodel::InteractionMsg intmsg = AvroHelper::getInstance()->decodeInteractionMsg("payload", msg->payload, msg->len);
        KINFO("Decoded InteractionMsg!");

        if (intmsg.MethodID == "node.position.set") {
            if (api) {  // ✅ Ensure api is not null before using
                KINFO("Handling position update for " << intmsg.MethodID);
                api->handleInteractionPositionUpdate(msg->timestamp, msg->st, intmsg);
            } else {
                KERROR("api is null in InteractionHandlerCommunication11p::handle()");
            }
        } else {
            KINFO("Method '" << intmsg.MethodID << "' is not known.");
        }
    } else {
        KDEBUG("Received message in unknown topic: " << topic);
        return false;
    }
    return true;
}

