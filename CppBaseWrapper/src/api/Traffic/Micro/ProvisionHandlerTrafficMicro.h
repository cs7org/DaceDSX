/*
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

#include "communication/ProvisionHandler.h"
#include "ProvisionTrafficMicro.h"

namespace daceDS {
class ProvisionHandlerTrafficMicro : public ProvisionHandler {

   public:
    ProvisionHandlerTrafficMicro(std::shared_ptr<Provision> p) : ProvisionHandler(p) { };
    virtual ~ProvisionHandlerTrafficMicro(){};

    bool handle(ConsumedMessage* msg) override;
};
}  // namespace daceDS
