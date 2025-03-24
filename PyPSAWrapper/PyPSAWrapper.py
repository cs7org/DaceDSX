#!/usr/bin/env python3
#
# Copyright (c) 2025 Informatik 7 Friedrich-Alexander Universität Erlangen-Nürnberg,
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#

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
from PyPSAApi import PyPSAAPI

config = configparser.ConfigParser()
config.read('config.properties')
print("HERE", config["general"])
broker = config["general"]["kafkaBroker"]
registry = config["general"]["schemaRegistry"]
baseDir = "/daceDS/CarlaWrapper/tmp/"
energySchemaPath = this_directory+"/../AvroSchemas/bus.avsc"

import json




class PyPSAWrapper():
    def __init__(self, scenarioID, instanceID):
        self.regexTopic = ["^provision\.simulation\." + scenarioID + "\.energy\.network"]
        self.topicPre = "provision.simulation." + scenarioID + ".energy."
        self.timeTopic = "orchestration.simulation." + scenarioID + ".sync"
        self.scetopic = ['provision.simulation.' + scenarioID + '.scenario']
        self.statusTopic = 'orchestration.simulation.' + scenarioID + '.status'
        self.restopic = ['provision.simulation.' + scenarioID + '.resource']
        self.other_instance_topics = []

        self.kid = scenarioID + "." + instanceID
        self.scenarioID = scenarioID
        self.instanceID = instanceID
        self.adoptList = []

        self.producer = KafkaProducer(broker, registry, self.kid, useAvro=True, schemaPath=energySchemaPath)
        self.statusProducer = KafkaProducer(broker, registry, self.kid, useAvro=False)
        self.jsonProducer = KafkaProducer(broker, registry, self.kid + "j", useAvro=False)
        self.consumer = None

        self.waitCounter = 0

        self.idMapping = {}
        # self.roadMapFile = None
        self.sim = None

        self.demoMode = False

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
        for sim in self.sce['buildingBlocks']:
            if sim['instanceID'] != self.instanceID:
                self.other_instance_topics.append(self.topicPre+sim['instanceID'])
                continue
            self.sim = sim
            for resID, resType in sim["resources"].items():
                if resType == "Network":
                    self.network = resID
            self.responsibility = sim['responsibilities']
            self.observers = sim['observers']

        if self.sim == None:
            print("no sim desc was found")
            sys.exit(1)

        self.klog("initialized")

        self.klog("waiting for resources")

        # fetching resources
        print("fetching network", self.network, flush=True)
        self.resConsumer = KafkaConsumer(broker, registry, self.restopic, self.kid + ".res")
        while True:
            try:
                print("before polling")
                res = self.resConsumer.poll(1)
                print("polling: ", res)
                if (res is None):
                    continue
                resource = res.value()
                print("received resource! ", resource, flush=True)
                l = -1
                print(((resource['File'] is None) and (resource['FileReference'] is None)), resource['File'], resource['FileReference'])
                if ((resource['File'] is None) and (resource['FileReference'] is None)):
                    continue
                if (resource['File'] is not None):
                    l = len(resource['File'])

                print(" id=", resource['ID'], " type=", resource['Type'], "file=", l, "bytes", flush=True)
                print("Network", self.network, resource['FileReference'])
                print((resource['File'] == self.network), (resource["Type"] == "Network"), flush=True)
                if ((resource['FileReference'] == self.network) and (
                        resource["Type"] == "Network")):  # would take sumo maps aswell
                    print("saving to disk", flush=True)
                    if (resource['File'] != None):
                        resBytes = resource['File']

                        newFile = open(baseDir + self.network, "wb")
                        for byte in resBytes:
                            newFile.write(byte.to_bytes(1, byteorder='big'))

                        newFile.close()

                    break
            except Exception as e:
                print("Unexpected error:", sys.exc_info()[0], flush=True)
                print("Unexpected error:", e, flush=True)
                time.sleep(1)
                print(".", end='', flush=True)

        ###############################
        ####### 2. start timing #######
        self.timeSync = TimeSync(broker, registry, self.timeTopic, self.kid + ".time",
                                 self.sce['execution']['syncedParticipants'], logging=False,
                                 timeoutHandler=self.handleTimeout)

        for p in self.regexTopic:
            self.timeSync.addExpectedPattern(p)

        self.timeSync.joinTiming()
        self.producer.create_topics([self.topicPre+"network"])

    def handleTimeout(self):
        print("handleTimeout", flush=True)
        self.startMainConsumer()

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
        print("\n in processMsg\n")
        if inMsg != None:
            print("== > > > received in ", inMsg.topic(), ", time =", inMsg.timestamp()[1], inMsg.value(), flush=True)
            # notify timesync about received msg
            timestamp = inMsg.timestamp()[1]  # 0 should be TIMESTAMP_CREATE_TIME
            topicBody = inMsg.topic()[len(self.topicPre):]
            subject, tmp = topicBody.split(".", 1)
            print("Subject: ", subject, flush=True)
            if subject == "network":
                line, load = tmp.split(".", 1)
                # special chars
                # edge = edge.replace("---2e", ".")
                realtopic = self.topicPre + subject + "." + line + "." + load
                print(inMsg.topic(), "->", realtopic)
                self.timeSync.notifiyAboutReceivedMessage(realtopic)
            else:
                self.timeSync.notifiyAboutReceivedMessage(subject)
                print(subject, "not supported jet")
                return

    def buses_to_observe(self):
        to_observe = []
        for observer in self.observers:
            if observer["task"] == "publish" and observer["element"] == "bus":
                for bus in observer["filter"].split(', '):
                    if bus not in to_observe:
                        to_observe.append(bus)
        return to_observe

    def run(self):
        print("\n\n_______________run_______________\n\n")
        try:

            self.klog("simulating")

            ### create api bridge and run  ######
            self.api = None
            stepLengthMs = self.sim['stepLength']
            stepLengthS = self.sim['stepLength'] / 1000
            # mapFile = baseDir + self.roadMapFile
            network_file = self.network
            network_file = self.network.split("///")[1]
            end = self.sce['simulationEnd']
            self.bbConsumer = KafkaConsumer(broker, registry, self.scetopic, self.kid + ".sce")
            self.api = PyPSAAPI(network_file, self.timeSync, self.bbConsumer, self.producer, self.scenarioID, self.other_instance_topics,self.instanceID, stepLengthS, self.sce['simulationEnd']/self.sim['stepLength'], to_observe=self.buses_to_observe())
            self.startMainConsumer()

            self.api.init(self.responsibility)

            iteration = 0
            while self.timeSync.currentLocalTime < end:

                # 1. ask to proceed
                sssl = stepLengthMs
                self.timeSync.timeAdvance(sssl)

                try:
                    self.api.prepareStep(iteration)
                except Exception as e:
                    print("prepareStep catched exception ")
                    print(e)

                    # 3.2. Makefile the sim step simulate

                try:
                    # todo: compute all steps until next sssl at once
                    self.api.step(iteration)
                except Exception as e:
                    print("step catched exception ")
                    print(e)
                # 4. process

                try:
                    self.api.processStep(iteration)
                except Exception as e:
                    print("processStep catched exception ")
                    print(e)

                try:
                    self.api.postStep(iteration, self.timeSync.currentLocalTime)
                except Exception as e:
                    print("postStep catched exception ")
                    print(e)
                iteration = iteration + 1
            self.klog("finished")

        except Exception as e:
            print("main loop catched exception - vvvvvvvv")
            print(e)
            print("main loop catched exception - ^^^^^^^")

        finally:
            if self.api is not None:
                self.api.destroy()
            if self.consumer is not None:
                self.consumer.stop()
            if self.timeSync is not None:
                self.timeSync.leaveTiming()
            # saving results
            # self.api.network.export_to_hdf5(os. getcwd() + "/" + self.instanceID+'_results')
            # self.api.network.buses_t.v_mag_pu.to_csv("/mnt/c/Users/seiwerth/Desktop/daceds4energy/_pypsa_results" + "/" +self.scenarioID +'_'+self.instanceID+'_results_v_mag_pu.csv', sep=';', index=True)
            # self.api.network.lines_t.p0.to_csv("/mnt/c/Users/seiwerth/Desktop/daceds4energy/_pypsa_results" + "/" +self.scenarioID +'_'+self.instanceID+'_results_p0.csv', sep=';', index=True)


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
        ctrl = PyPSAWrapper(scenarioID ,instanceID)
        print("created Wrapper:", ctrl)
        if scenarioID[0:4] == "demo":
            ctrl.demoMode = True

        ctrl.prepare()
        ctrl.run()

    except KeyboardInterrupt:
        print('\nCancelled by user. Bye!')


if __name__ == '__main__':
    main()