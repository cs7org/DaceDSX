*/*
MIT License

Copyright 2021 Moritz Gütlein

This code was originally published under the Apache 2.0 License (http://www.apache.org/licenses/LICENSE-2.0) in 2021.
In 2025, it has been relicensed under the MIT License (https://choosealicense.com/licenses/mit/) with the explicit permission of all copyright holders.
*/
#pragma once

#include <csignal>
#include <iostream>
#include <stdexcept>
#include <thread>

#include "MessageHandler.h"
#include "util/Config.h"
#include "util/Defines.h"
#include "util/log.h"

namespace daceDS {
class LogHandler : public MessageHandler {
   public:
    LogHandler() : MessageHandler(){};
    virtual ~LogHandler(){};

    bool handle(ConsumedMessage* msg) override;
};
}  // namespace daceDS
