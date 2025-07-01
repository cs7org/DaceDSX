{
  "scenarioID": "UC7",
  "simulationStart": 0,
  "simulationEnd": 1000,
  "domainReferences": {},
  "execution": {
    "randomSeed": 123,
    "constraints": "",
    "priority": 0,
    "syncedParticipants": 3
  },
  "buildingBlocks": [
   {
      "instanceID": "SumoWrapper1",
      "type": "SumoWrapper",
      "layer": "micro",
      "domain": "traffic",
      "isExternal": false,
      "stepLength": 1,
      "parameters": {
        "ghosting": "false"
      },
      "resources": {
       "erlangen.net.xml": "RoadMap",
        "erlangen.poly.xml": "Additional",
        "erlangen.rou.xml": "Traffic"
      },
      "results": {},
      "synchronized": true,
      "responsibilities": [],
      "observers": [
        {
          "task": "publish",
          "element": "vehicle",
          "filter": "",
          "period": 1,
          "trigger": "",
          "type": "avro"
        }
      ],
      "customparams": ""
    },
    {
      "instanceID": "OMNeTWrapper2",
      "type": "OMNeTWrapper",
      "layer": "80211p",
      "domain": "communication",
      "stepLength": 1,
      "isExternal": false,
      "parameters": {
        "ghosting": "false", 
        "equipped": "1" ,
        "beaconing" : "1"
      },
      "resources": {},
      "results": {},
      "synchronized": true,
      "responsibilities": [],
      "observers": [],
      "customparams": ""
    }
  ],
  "translators": [],
  "projectors": [
  {
    "projectorID": "V2XProjector1",
    "type": "V2XProjector",
    "domainA": "traffic",
    "layerA": "micro",
    "domainB": "communication",
    "layerB": "80211p",
    "resources": {},
    "parameters": {
      "sceID": "UC7",
      "enableLogging": "true"
    }
  }
]
}

