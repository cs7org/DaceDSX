/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *     https://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */


#ifndef CPP_RADIOMSG_HH_3474550749__H_
#define CPP_RADIOMSG_HH_3474550749__H_


#include <sstream>
#include "boost/any.hpp"
#include "avro/Specific.hh"
#include "avro/Encoder.hh"
#include "avro/Decoder.hh"

namespace daceDS {
namespace datamodel {
struct RadioMsg {
    std::string sender;
    int64_t sendTime;
    std::string receiver;
    int64_t receiveTime;
    std::map<std::string, std::string > data;
    RadioMsg() :
        sender(std::string()),
        sendTime(int64_t()),
        receiver(std::string()),
        receiveTime(int64_t()),
        data(std::map<std::string, std::string >())
        { }
};

}
}
namespace avro {
template<> struct codec_traits<daceDS::datamodel::RadioMsg> {
    static void encode(Encoder& e, const daceDS::datamodel::RadioMsg& v) {
        avro::encode(e, v.sender);
        avro::encode(e, v.sendTime);
        avro::encode(e, v.receiver);
        avro::encode(e, v.receiveTime);
        avro::encode(e, v.data);
    }
    static void decode(Decoder& d, daceDS::datamodel::RadioMsg& v) {
        if (avro::ResolvingDecoder *rd =
            dynamic_cast<avro::ResolvingDecoder *>(&d)) {
            const std::vector<size_t> fo = rd->fieldOrder();
            for (std::vector<size_t>::const_iterator it = fo.begin();
                it != fo.end(); ++it) {
                switch (*it) {
                case 0:
                    avro::decode(d, v.sender);
                    break;
                case 1:
                    avro::decode(d, v.sendTime);
                    break;
                case 2:
                    avro::decode(d, v.receiver);
                    break;
                case 3:
                    avro::decode(d, v.receiveTime);
                    break;
                case 4:
                    avro::decode(d, v.data);
                    break;
                default:
                    break;
                }
            }
        } else {
            avro::decode(d, v.sender);
            avro::decode(d, v.sendTime);
            avro::decode(d, v.receiver);
            avro::decode(d, v.receiveTime);
            avro::decode(d, v.data);
        }
    }
};

}
#endif
