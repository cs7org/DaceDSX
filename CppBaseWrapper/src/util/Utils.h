/*
MIT License

Copyright 2021 Moritz Gütlein

This code was originally published under the Apache 2.0 License (http://www.apache.org/licenses/LICENSE-2.0) in 2021.
In 2025, it has been relicensed under the MIT License (https://choosealicense.com/licenses/mit/) with the explicit permission of all copyright holders.
*/

#pragma once

#include <sys/time.h>
#include <time.h>
#include <unistd.h>

#include <algorithm>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>
#include <filesystem>

#include "datamodel/Scenario.hh"
#include "datamodel/BB.hh"
#include "util/Defines.h"
#include "util/log.h"
#include "util/Config.h"

namespace daceDS {

void createDirs();
std::string GetCurrentWorkingDir(void);
std::vector<std::string> split(const std::string& s, char delimiter);
std::string concat(std::vector<std::string> v, char delimiter);
bool isValidAttributeStr(std::string att);
const std::string getCurrentDate();
static void printSce(datamodel::Scenario& s, datamodel::BB& t);

std::string strReplace(std::string s, std::string from, std::string to);
std::string escapeSpecialChars(std::string s);
std::string decodeSpecialChars(std::string s);
}  // namespace daceDS
