from owlready2 import *
import logging
import sys
import time
import configparser
import os

this_directory=os.path.dirname(os.path.abspath(__file__))

sys.path.append(this_directory+'/../PythonBaseWrapper/src/logic')
sys.path.append(this_directory+'/../PythonBaseWrapper/src/communication')
from TimeSync import TimeSync
from KafkaConsumer import KafkaConsumer
from KafkaProducer import KafkaProducer
from MessageBuffer import MessageBuffer, getMsgSender
import traceback
import networkx as nx
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import yaml
from  time import sleep

config = configparser.ConfigParser()
config.read(this_directory+'/config.properties')
broker = config["general"]["kafkaBroker"]
registry = config["general"]["schemaRegistry"]
baseDir = "/daceDS/CarlaWrapper/tmp/"
schemaPath = this_directory+"/../AvroSchemas/"
onto = get_ontology("file://"+this_directory+"/ontology.owl").load()

@dataclass
class Attribute:
    name: str
    description: str
    ontology_concept: Optional[str]
    unit: Optional[str]
    type: Optional[str]
    raw_data: dict = field(default_factory=dict)

@dataclass
class Component:
    name: str
    description: str
    ontology_concept: Optional[str]
    attributes: Dict[str, Attribute] = field(default_factory=dict)


class OntologyTransformer():
    def __init__(self, scenarioID, instanceID):
        self.regexTopic = ["^provision\.simulation\." + scenarioID + "\.energy"]
        self.topicPre = "provision.simulation." + scenarioID + ".energy."
        self.timeTopic = "orchestration.simulation." + scenarioID + ".sync"
        self.scetopic = ['provision.simulation.' + scenarioID + '.scenario']
        self.statusTopic = 'orchestration.simulation.' + scenarioID + '.status'
        self.restopic = ['provision.simulation.' + scenarioID + '.resource']

        self.kid = scenarioID + "." + instanceID
        self.scenarioID = scenarioID
        self.instanceID = instanceID
        self.adoptList = []
        self.parameters = []

        # self.producer = KafkaProducer(broker, registry, self.kid, useAvro=True, schemaPath=energySchemaPath)
        self.statusProducer = KafkaProducer(broker, registry, self.kid, useAvro=False)
        self.jsonProducer = KafkaProducer(broker, registry, self.kid + "j", useAvro=False)
        self.consumer = None

        self.waitCounter = 0

        self.idMapping = {}
        # self.roadMapFile = None
        self.sim = None

        self.demoMode = False
        self.timestep = 0
        # filled by the main consumer thread, translated in the simulation loop
        self.inbox = MessageBuffer()
        self.publish_topics = None






    def klog(self, msg):
        print("klog:", self.statusTopic, self.instanceID + ": " + msg)
        self.statusProducer.produce(self.statusTopic, self.instanceID + ": " + msg)

    def publishObservation(self, topic, value):
        # print("trying to publish on topic="+topic+": "+value)
        self.jsonProducer.produce(topic, value, timestamp=self.timeSync.currentLocalTime)

    def prepare(self):
        self.klog("started")

        #################################
        ####### 1. get more info ########
        self.sceConsumer = KafkaConsumer(broker, registry, self.scetopic, self.kid + ".sce")
        self.sce = None
        while self.sce == None:
            try:
                msg = self.sceConsumer.poll(1)
                if (msg is not None):
                    print("got return from poll", flush=True)
                    self.sce = msg.value()
                else:
                    print("got null return from poll", flush=True)
            except Exception as e:
                print("Unexpected error:", sys.exc_info()[0], flush=True)
                print("Unexpected error:", e, flush=True)
                time.sleep(1)
                print(".", end='', flush=True)
            print("polling for sce", flush=True)
        self.sceConsumer.stop()
        print("got sce", flush=True)

        ##get resources
        for sim in self.sce['translators']:
            if sim['translatorID'] == self.instanceID:
                self.sim = sim
                self.responsibilityA = sim['responsibilitiesA']
                self.responsibilityB = sim['responsibilitiesB']
                self.layerA = sim["layerA"].split(", ")
                self.layerB = sim["layerB"].split(", ")

                self.resources = sim['resources']
                self.parameters = sim['parameters']

        if self.sim == None:
            print("no sim desc was found")
            sys.exit(1)
        for bb in self.sce['buildingBlocks']:
            if bb["synchronized"] == True and bb["stepLength"] > self.timestep:
                self.timestep = bb["stepLength"]
        self.klog("initialized")

        self.klog("waiting for resources")

        # fetching resources
        # print("fetching network", self.network, flush=True)
        self.resConsumer = KafkaConsumer(broker, registry, self.restopic, self.kid + ".res")
        self.timeSync = TimeSync(broker, registry, self.timeTopic, self.kid + ".time",
                                 self.sce['execution']['syncedParticipants'], logging=False,
                                 timeoutHandler=self.handleTimeout)

        for p in self.regexTopic:
            self.timeSync.addExpectedPattern(p)

        self.timeSync.joinTiming()
        # self.producer.create_topics([self.topicPre+"network"])


    def handleTimeout(self):
        # restarting the consumer would re-deliver uncommitted messages, the consumer
        # picks up new topics by itself (metadata refresh), so only report what is missing
        print("handleTimeout: still waiting for", self.timeSync.expectedReceiveCount,
              "received", self.timeSync.actualReceivedMsgCount, flush=True)

    def startMainConsumer(self):
        if (self.consumer is not None):
            self.consumer.stop()
            time.sleep(1)
            self.waitCounter += 1

        if (len(self.timeSync.inferedTopics) > 0):
            print("1 (re)subscribing to", self.timeSync.inferedTopics)
            self.consumer = KafkaConsumer(broker, registry, self.timeSync.inferedTopics, self.kid + "_consumer",
                                          cb=self.processMsg)
        else:
            print("2 (re)subscribing to", self.regexTopic)
            self.consumer = KafkaConsumer(broker, registry, self.regexTopic, self.kid + "_consumer", cb=self.processMsg)

        self.consumer.listenInBG()

    def processMsg(self, inMsg):
        # print("\n in processMsg\n")
        if inMsg != None:
            # print("== > > > received in ", inMsg.topic(), ", time =", inMsg.timestamp()[1], inMsg.value(), flush=True)
            # notify timesync about received msg
            timestamp = inMsg.timestamp()[1]  # 0 should be TIMESTAMP_CREATE_TIME
            topicBody = inMsg.topic()[len(self.topicPre):]
            subject, tmp = topicBody.split(".", 1)
            # print("Subject: ", subject, flush=True)
            # translation happens in the simulation loop (run), not in this consumer thread.
            # our own output is only counted, translating it again could create loops
            if not getMsgSender(inMsg).startswith(self.kid + "."):
                self.inbox.add(inMsg)
            if subject == "PV" or subject == "Battery" or subject == "Bus":
                bus = tmp.split(".", 1)[0]
                # special chars
                # edge = edge.replace("---2e", ".")
                realtopic = self.topicPre + subject + "." + bus
                # print(inMsg.topic(), "->", realtopic)
                self.timeSync.notifiyAboutReceivedMessage(inMsg.topic())
            else:
                self.timeSync.notifiyAboutReceivedMessage(inMsg.topic())
                print(subject, "not supported jet")
                return

    # def mapping_layers(self):
    #     mapping = {}
    #     for layer in self.layerA.split(", "):
    #         # finde alle verbundenden therms

    def build_graph(self):

        G = nx.DiGraph()

        for cls in onto.classes():

            for prop in cls.get_class_properties():

                try:
                    values = prop[cls]

                    for value in values:

                        if hasattr(value, "name"):
                            G.add_edge(
                                cls.name,
                                value.name,
                                relation=prop.name
                            )

                except:
                    pass

        return G

    def has_descendant(self, G,concept, descendant):

        if concept not in G:
            return False

        reachable = nx.descendants(G, concept)

        return descendant in reachable

    def build_bus_index(self, building_blocks):
        """
        Per layer, which buses a building block provides data for and which it consumes data for:
        - provides: its observers, the bus it is connected to ("bus") and its copy buses
        - consumes: the bus it takes its setpoint from ("slack") and its copy buses
        e.g. the battery consumes the slack power but only publishes its own state at "bus",
        so nothing may be translated into its output topic.
        """
        provides, consumes = {}, {}
        for layer in self.layerA + self.layerB:
            provides[layer] = []
            consumes[layer] = []

        def split(value):
            return [b.strip() for b in value.split(",")]

        for block in building_blocks:
            layer = block["layer"]
            params = block.get("parameters", {})
            for obs in block["observers"]:
                provides[layer].extend(split(obs["filter"]))

            if "bus" in params:
                provides[layer].extend(split(params["bus"]))
            if "slack" in params:
                consumes[layer].extend(split(params["slack"]))

            # Spezialfall: Bus-Layer selbst, copy buses are exchanged in both directions
            if "copy_buses" in params:
                provides[layer].extend(split(params["copy_buses"]))
                consumes[layer].extend(split(params["copy_buses"]))

        return provides, consumes

    def build_translator_map(self, translator, provides, consumes):
        # layerA = [x.strip() for x in translator["layerA"].split(",")]
        # layerB = [x.strip() for x in translator["layerB"].split(",")]

        result = {}

        for layer_a in self.layerA:
            for layer_b in self.layerB:
                if layer_a == layer_b:
                    continue

                # only buses layer_a publishes and layer_b expects as input
                intersection = list(set(provides[layer_a]) & set(consumes[layer_b]))
                if intersection:
                    # setdefault: several target layers for the same source must not overwrite each other
                    result.setdefault(layer_a, {})[layer_b] = intersection

        return result



    # -------------------------------------------------
    # YAML laden
    # -------------------------------------------------

    def load_yaml(self, filepath):

        with open(filepath, "r", encoding="utf-8") as file:
            data = yaml.safe_load(file)

        components = {}

        for component_name, component_data in data.items():

            component = Component(
                name=component_name,
                description=component_data.get("Description"),
                ontology_concept=component_data.get("NearestOntologyConcept"),
            )

            attributes = component_data.get("Attributes", {})

            for attr_name, attr_data in attributes.items():
                attribute = Attribute(
                    name=attr_name,
                    description=attr_data.get("Description"),
                    ontology_concept=attr_data.get("NearestOntologyConcept"),
                    unit=attr_data.get("Unit"),
                    type=attr_data.get("Type"),
                    raw_data=attr_data,
                )

                component.attributes[attr_name] = attribute

            components[component_name] = component

        return components

    def get_infos_and_message_format(self, yaml1):
        message_dict = {}
        info_dict = {}
        for comp in yaml1.values():
            print(comp)
            for attribute in comp.attributes.values():
                concept = attribute.ontology_concept
                unit = attribute.unit
                name = attribute.name
                type = attribute.type
                print(concept, unit)
                info_dict[name] = {
                    "concept": concept,
                    "unit": unit,
                    "type": type
                }
                message_dict[name] = None
        return info_dict, message_dict

    def check_compatibility(self):
        self.layer_dict = {}
        yaml_paths = set()
        yamls = []

        G = self.build_graph()
        for layer in self.layerA:
            yaml_paths.add(this_directory+"/../_data/layers/"+str(layer)+".yml")
            self.has_descendant(G, layer, "ElectricalEnergy")
        for layer in self.layerB:
            yaml_paths.add(this_directory+"/../_data/layers/"+str(layer)+".yml")
            self.has_descendant(G, layer, "ElectricalEnergy")
        for path in yaml_paths:
            yamls.append(self.load_yaml(path))
        for yml in yamls:
            for key in yml.keys():
                infos, message_format = self.get_infos_and_message_format(yml)
                self.layer_dict[key] = {"infos": infos,
                                   "message": message_format}
                print(len(message_format.keys()))
        provides, consumes = self.build_bus_index(self.sce["buildingBlocks"])
        self.mappings = self.build_translator_map(self.sce["translators"], provides, consumes)
        print("translator mappings:", self.mappings, flush=True)


    def run(self):
        print("\n\n_______________run_______________\n\n")
        self.check_compatibility()
        self.klog("simulating")

        print("HERE layerB", self.layerB)
        self.producers={}
        for layer in self.layerB:
            # own producer ID per layer, processMsg uses the 'sender' header to skip our own output
            self.producers[layer] = KafkaProducer(broker, registry, self.kid + "." + layer, useAvro=True, schemaPath=f"{schemaPath}{layer}.avsc")

        ### create api bridge and run  ######
        stepLengthMin = self.timestep
        end = self.sce['simulationEnd']
        self.startMainConsumer()
        try:
            while self.timeSync.currentLocalTime < end:
                print("IN LOOP")

                # 1. ask to proceed
                self.timeSync.timeAdvance(stepLengthMin)

                # every participant creates its topics before its first time request,
                # so after our first advance all publish topics exist (replaces the old sleep(5))
                if self.publish_topics is None:
                    self.publish_topics = self.find_publish_topics()

                # 2. translate everything that was sent before the current time. The results are
                # announced with our next time request, so receivers process them in their next step
                for msg in self.inbox.take(self.timeSync.currentLocalTime):
                    try:
                        self.translate_process_msg(msg)
                    except Exception:
                        print("translation failed for message on", msg.topic(), flush=True)
                        traceback.print_exc()

            self.klog("finished")
        finally:
            if self.consumer is not None:
                self.consumer.stop()
            if self.timeSync is not None:
                self.timeSync.leaveTiming()

    def find_publish_topics(self):
        publish_topics = {}
        for layer in self.layerB:
            all_topics = self.producers[layer].all_topics()
            topics = []
            for val in self.mappings.values():
                if layer in val.keys():
                    for resp in val[layer]:
                        print("layer", layer, "resp", resp)
                        topics.extend(t for t in all_topics if "."+str(layer)+"." in t and str(resp).replace(" ", "_") in t and self.scenarioID in t)
            print("Publish Topics", topics)
            publish_topics[layer] = topics
        return publish_topics

    def translate_process_msg(self, msg):
        topic = msg.topic()
        value = msg.value()
        topic_parts = topic.split(self.topicPre)[-1].split(".")
        msg_layer = topic_parts[0]
        msg_resp = topic_parts[-1]
        process = False
        for key in self.mappings.keys():
            if key == msg_layer:
                process=True
        if process:
            for layer_b in self.mappings[msg_layer]:
                for resp in self.mappings[msg_layer][layer_b]:
                    print("msg_resp", msg_resp, self.mappings[msg_layer][layer_b],
                          str(self.mappings[msg_layer][layer_b]).replace(" ", "_"))
                    if msg_resp in str(resp).replace(" ", "_"):
                        print("TRANSLATING")
                        trans_msg = self.translate_message(value, msg_layer, layer_b, self.layer_dict, resp)
                        print("finished translating", trans_msg)
                        for tpc in self.publish_topics[layer_b]:
                            if tpc.endswith(msg_resp):
                                print("publishing msg to topic", tpc, trans_msg)
                                self.producers[layer_b].produce(tpc, trans_msg, timestamp=self.timeSync.currentLocalTime)
                                self.timeSync.notifiyAboutSentMessage(tpc)

    def translate_unit(self, value, unitA, unitB):
        print("___ in translate_unit ___")
        if unitA == None or unitB == None:
            print("could not convert value", value, "from", unitA, "to", unitB)
        if unitA == unitB:
            return value
        elif len(unitA) == len(unitB):
            if unitA[0] == "k" and unitB[0] == "M":
                return float(value) * 1e-3
            elif unitA[0] == "M" and unitB[0] == "k":
                return float(value) * 1e3
            else:
                print("could not convert value", value, "from", unitA, "to", unitB)
        elif len(unitA) > len(unitB):
            if unitA[0] == "k":
                return float(value) * 1e3
            elif unitA[0] == "M":
                return float(value) * 1e6
            else:
                print("could not convert value", value, "from", unitA, "to", unitB)
        else:
            if unitB[0] == "k":
                return float(value) * 1e-3
            elif unitB[0] == "M":
                return float(value) * 1e-6
            else:
                print("could not convert value", value, "from", unitA, "to", unitB)

    def convert_type(self, value, type):
        print("__ in convert type __")
        if type == "str":
            return str(value)
        elif type == "int":
            return int(value)
        elif type == "float":
            return float(value)
        else:
            print("Type", type, "is not defined")

    def translate_message(self, msg, layerA, layerB, layer_dict, resp):
        print("__in translate_message__")
        info_layerA = layer_dict[layerA]['infos']
        info_layerB = layer_dict[layerB]['infos']
        msg_format_layerB = layer_dict[layerB]['message']
        new_msg = {}
        print("layerB", layerB, "layerA", layerA)
        for msg_field in msg_format_layerB.keys():
            print("msg_field", msg_field)
            filled = False
            for val in info_layerA.keys():
                # print("Alle infos",info_layerA, val, info_layerB, msg_field)
                if info_layerA[val]["concept"] == info_layerB[msg_field]["concept"]:
                    print("HERE1")
                    print(msg, val, msg_field)
                    value = self.translate_unit(msg[val], info_layerA[val]["unit"], info_layerB[msg_field]["unit"])
                    print("HERE2")
                    value = self.convert_type(value, info_layerB[msg_field]["type"])
                    print("HERE3")
                    # no sign flip for Bus -> Battery: a positive slack power (grid import) maps to a
                    # positive battery power, which the battery treats as discharge (feed-in convention)
                    new_msg[msg_field] = value
                    print("HERE4")
                    filled = True
            if not filled:
                if msg_field == "control type" or msg_field == "control":
                    value = "PQ"
                elif msg_field == "name" and layerB == "Bus":
                    # Todo if network, get bus name from topic .split(".")[-2]
                    value = str(resp)
                else:
                    # Todo actually define default values and for more complex stuff try and calculate missing values
                    value = self.convert_type(0, info_layerB[msg_field]["type"])
                print("HERE5")
                new_msg[msg_field] = value
        return new_msg



def main():
    if (len(sys.argv) > 1):
        scenarioID = sys.argv[1]
        instanceID = sys.argv[2]
    else:
        print("No SceID & SimID provided, using demo input")

        from datetime import datetime
        date_time = datetime.now()
        scenarioID = "demo " +date_time.strftime("%m%d%H%M%S")
        instanceID = "carla0  "  # +date_time.strftime("%m/%d/%Y, %H:%M:%S")
    print(scenarioID, instanceID)

    try:
        ctrl = OntologyTransformer(scenarioID ,instanceID)
        print("created Wrapper:", ctrl)
        if scenarioID[0:4] == "demo":
            ctrl.demoMode = True

        ctrl.prepare()
        ctrl.run()

    except KeyboardInterrupt:
        print('\nCancelled by user. Bye!')


if __name__ == '__main__':
    main()