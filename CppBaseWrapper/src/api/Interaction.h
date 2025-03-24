/*
MIT License

Copyright 2021 Moritz Gütlein

This code was originally published under the Apache 2.0 License (http://www.apache.org/licenses/LICENSE-2.0) in 2021.
In 2025, it has been relicensed under the MIT License (https://choosealicense.com/licenses/mit/) with the explicit permission of all copyright holders.
*/

#pragma once

#include <exception>
#include <memory>
#include <string>
#include <map>
#include <vector>

#include "util/Config.h"
#include "util/Defines.h"


namespace daceDS {
class Interaction {
   public:
    Interaction(){};
    virtual ~Interaction(){};

    static std::vector<std::string> methods;
    static std::vector<std::string> getMethods() {
        return methods;
    }

};
}  // namespace daceDS
