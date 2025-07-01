cplusplus {{
    #include "veins/base/utils/SimpleAddress.h"   
    #include "veins/modules/messages/BaseFrame1609_4_m.h"         // address type
    #include <map>
    #include <string>

    // STL map used as field type
    typedef std::map<std::string, std::string> Datamap;
}}

class noncobject Datamap;   // tell OMNeT++ not to serialise the map itself


namespace veins;
class BaseFrame1609_4;
     
packet RadioMessage extends BaseFrame1609_4
{
    string  sender;     // who created the message
    string  payload;    // arbitrary text payload
    Datamap data;       // user-defined key/value pairs
}
