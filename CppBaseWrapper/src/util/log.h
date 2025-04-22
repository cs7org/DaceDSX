/*
MIT License

Copyright 2021 Moritz Gütlein

This code was originally published under the Apache 2.0 License (http://www.apache.org/licenses/LICENSE-2.0) in 2021.
In 2025, it has been relicensed under the MIT License (https://choosealicense.com/licenses/mit/) with the explicit permission of all copyright holders.
*/
#pragma once

#include <iostream>
#include <sstream>
#include <string>

#include "Utils.h"

namespace daceDS {

#ifdef KDEBUG3
#define KDEBUG3(msg)                                                                                        \
    do {                                                                                                   \
        std::cout << daceDS::getCurrentDate() << " | KDEBUG3 " << __PRETTY_FUNCTION__ << " | " << msg << std::endl; \
    } while (false)
#else
#define KDEBUG3(msg) do { } while (false)
#endif

#ifdef KDEBUG
#define KDEBUG(msg) \
    do {             \
        std::cout << getCurrentDate() << " | [DEBUG] " << __PRETTY_FUNCTION__ << " | " << msg << std::endl; \
    } while (false)
#else
#define KDEBUG(msg) do { } while (false) 
#endif

#define KERROR(msg) \
    do {             \
        std::cout << getCurrentDate() << " | [ERROR] " << __PRETTY_FUNCTION__ << " | " << msg << std::endl; \
    } while (false)
// #define KERROR(msg) do { } while (false)


#define KINFO(msg) \
    do {             \
        std::cout << getCurrentDate() << " | [INFO] " << __PRETTY_FUNCTION__ << " | " << msg << std::endl; \
    } while (false)



#ifdef KDBGCB
#define KDBGCB(msg) \
    do {             \
        std::cout << getCurrentDate() << " | [DBGCB] " << __PRETTY_FUNCTION__ << " | " << msg << std::endl; \
    } while (false)
#else
#define KDBGCB(msg) do { } while (false) 
#endif

#ifdef DS_BASE_DBG
#define DS_BASE_DBG(msg) \
    do {             \
        std::cout << getCurrentDate() << " | [DS_BASE_DBG] " << __PRETTY_FUNCTION__ << " | " << msg << std::endl; \
    } while (false)
#else
#define DS_BASE_DBG(msg) do { } while (false) 
#endif

#ifdef DS_AVRO_DBG
#define DS_AVRO_DBG(msg) \
    do {             \
        std::cout << getCurrentDate() << " | [DS_AVRO_DBG] " << __PRETTY_FUNCTION__ << " | " << msg << std::endl; \
    } while (false)
#else
#define DS_AVRO_DBG(msg) do { } while (false) 
#endif



#ifdef DS_CTRL_DBG
#define DS_CTRL_DBG(msg) \
    do {             \
        std::cout << getCurrentDate() << " | [DS_CTRL_DBG] " << __PRETTY_FUNCTION__ << " | " << msg << std::endl; \
    } while (false)
#else
#define DS_CTRL_DBG(msg) do { } while (false) 
#endif

#ifdef DS_SYNC_DBG
#define DS_SYNC_DBG(msg) \
    do {             \
        std::cout << getCurrentDate() << " | [DS_SYNC_DBG] " << __PRETTY_FUNCTION__ << " | " << msg << std::endl; \
    } while (false)
#else
#define DS_SYNC_DBG(msg) do { } while (false) 
#endif




#ifdef DSTRAFFIC_TRANSFER_DBG
#define DSTRAFFIC_TRANSFER_DBG(msg) \
    do {             \
        std::cout << getCurrentDate() << " | [DSTRAFFIC_TRANSFER_DBG] " << __PRETTY_FUNCTION__ << " | " << msg << std::endl; \
    } while (false)
#else
#define DSTRAFFIC_TRANSFER_DBG(msg) do { } while (false) 
#endif


#ifdef DSTRAFFIC_CTRL_DBG
#define DSTRAFFIC_CTRL_DBG(msg) \
    do {             \
        std::cout << getCurrentDate() << " | [DSTRAFFIC_CTRL_DBG] " << __PRETTY_FUNCTION__ << " | " << msg << std::endl; \
    } while (false)
#else
#define DSTRAFFIC_CTRL_DBG(msg) do { } while (false) 
#endif

#ifdef DSTRAFFIC_MEASURE_DBG
#define DSTRAFFIC_MEASURE_DBG(msg) \
    do {             \
        std::cout << getCurrentDate() << " | [DSTRAFFIC_MEASURE_DBG] " << __PRETTY_FUNCTION__ << " | " << msg << std::endl; \
    } while (false)
#else
#define DSTRAFFIC_MEASURE_DBG(msg) do { } while (false) 
#endif





}