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


#ifndef CPP_VEC3_HH_3631740942__H_
#define CPP_VEC3_HH_3631740942__H_


#include <sstream>
#include "boost/any.hpp"
#include "avro/Specific.hh"
#include "avro/Encoder.hh"
#include "avro/Decoder.hh"

namespace daceDS {
namespace datamodel {
struct Vec3 {
    double x;
    double y;
    double z;
    Vec3() :
        x(double()),
        y(double()),
        z(double())
        { }
};

}
}
namespace avro {
template <class T> struct codec_traits;
template<> struct codec_traits<daceDS::datamodel::Vec3> {
    static void encode(Encoder& e, const daceDS::datamodel::Vec3& v) {
        avro::encode(e, v.x);
        avro::encode(e, v.y);
        avro::encode(e, v.z);
    }
    static void decode(Decoder& d, daceDS::datamodel::Vec3& v) {
        if (avro::ResolvingDecoder *rd =
            dynamic_cast<avro::ResolvingDecoder *>(&d)) {
            const std::vector<size_t> fo = rd->fieldOrder();
            for (std::vector<size_t>::const_iterator it = fo.begin();
                it != fo.end(); ++it) {
                switch (*it) {
                case 0:
                    avro::decode(d, v.x);
                    break;
                case 1:
                    avro::decode(d, v.y);
                    break;
                case 2:
                    avro::decode(d, v.z);
                    break;
                default:
                    break;
                }
            }
        } else {
            avro::decode(d, v.x);
            avro::decode(d, v.y);
            avro::decode(d, v.z);
        }
    }
};

}
#endif
