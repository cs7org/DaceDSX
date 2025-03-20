/*
MIT License

Copyright 2021 Moritz Gütlein

This code was originally published under the Apache 2.0 License (http://www.apache.org/licenses/LICENSE-2.0) in 2021.
In 2025, it has been relicensed under the MIT License (https://choosealicense.com/licenses/mit/) with the explicit permission of all copyright holders.
*/
#pragma once

#include <librdkafka/rdkafkacpp.h>
#include <signal.h>

#include <csignal>
#include <iostream>
#include <stdexcept>
#include <thread>

#include "communication/Consumer.h"
#include "communication/ConsumedMessage.h"
#include "util/Config.h"
#include "util/Defines.h"
#include "util/log.h"

using std::cout;
using std::endl;
using std::exception;
using std::string;

/**
 * Based on the cppkafka examples
 * */
namespace daceDS {
// class ExampleConsumeCb : public RdKafka::ConsumeCb {
//    public:
//     void consume_cb(RdKafka::Message &msg, void *opaque) {
//         //msg_consume(&msg, opaque);
//     }
// };
class KafkaConsumer : public Consumer {
    RdKafka::Conf *conf = 0;
    RdKafka::Conf *tconf = 0;
    bool exit_eof = false;
    volatile sig_atomic_t run = 1;
    std::vector<std::string> _topics;
    //ExampleDeliveryReportCb ex_dr_cb;

   public:
    // RdKafka::Consumer *consumer = 0;
    // RdKafka::Queue *queue = 0;
    RdKafka::KafkaConsumer *consumer = 0;
    std::thread t1;
    KafkaConsumer(std::shared_ptr<MessageHandler> hdl, bool counting = false) : Consumer(hdl, counting){};
    virtual ~KafkaConsumer() { delete consumer; };

    void msg_consume(RdKafka::Message *message, void *opaque);
    void subscribe(std::string broker, std::vector<std::string> &topic, std::string group_id, std::string loglevel = "");
    virtual void listen();
    virtual void stop();
};
}  // namespace daceDS
