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
from pvlibApi import pvlibAPI

config = configparser.ConfigParser()
config.read('config.properties')
broker = config["general"]["kafkaBroker"]
registry = config["general"]["schemaRegistry"]
baseDir = "/daceDS/CarlaWrapper/tmp/"
energySchemaPath = this_directory+"/../AvroSchemas/PV.avsc"

import json




class pvlibWrapper():
    def __init__(self, scenarioID, instanceID):
        self.regexTopic = ["^provision\.simulation\." + scenarioID + "\.energy\.PV"]
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
        self.parameters = []

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
            self.responsibility = sim['responsibilities']
            self.observers = sim['observers']
            self.parameters = sim['parameters']

        if self.sim == None:
            print("no sim desc was found")
            sys.exit(1)

        self.klog("initialized")

        self.klog("waiting for resources")

        ###############################
        ####### 2. start timing #######
        self.timeSync = TimeSync(broker, registry, self.timeTopic, self.kid + ".time",
                                 self.sce['execution']['syncedParticipants'], logging=False,
                                 timeoutHandler=self.handleTimeout)

        # for p in self.regexTopic:
        #     self.timeSync.addExpectedPattern(p)

        self.timeSync.joinTiming()
        self.producer.create_topics([self.topicPre+"pv"])

    def handleTimeout(self):
        print("handleTimeout", flush=True)
        # self.startMainConsumer()

    def startMainConsumer(self):
        print("Main Consumer", flush=True)
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
            if subject == "PV":
                bus = tmp.split(".", 1)
                # special chars
                # edge = edge.replace("---2e", ".")
                print("\n",bus,"\n")
                realtopic = self.topicPre + subject + "." + bus[0]
                print(inMsg.topic(), "->", realtopic)
                self.timeSync.notifiyAboutReceivedMessage(realtopic)
            else:
                self.timeSync.notifiyAboutReceivedMessage(subject)
                print(subject, "not supported jet")
                return

    def run(self):
        print("\n\n_______________run_______________\n\n")
        try:

            self.klog("simulating")

            ### create api bridge and run  ######
            self.api = None
            stepLengthMin = self.sim['stepLength']
            stepLengthS = self.sim['stepLength'] * 60
            end = self.sce['simulationEnd']
            # self.bbConsumer = KafkaConsumer(broker, registry, self.scetopic, self.kid + ".sce")
            self.api = pvlibAPI(self.timeSync, self.producer, self.scenarioID, self.instanceID, stepLengthMin, self.sce['simulationEnd']/self.sim['stepLength'], to_observe=[], parameters=self.parameters)
            self.startMainConsumer()

            self.api.init()
            # print("participants =", self.timeSync.participants)

            iteration = 0
            while self.timeSync.currentLocalTime < end:

                # 1. ask to proceed
                sssl = stepLengthMin

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
                    self.api.processStep()
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
            self.api.write_results()
            if self.api is not None:
                self.api.destroy()
            if self.consumer is not None:
                self.consumer.stop()
            if self.timeSync is not None:
                self.timeSync.leaveTiming()



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
        ctrl = pvlibWrapper(scenarioID ,instanceID)
        print("created Wrapper:", ctrl)
        if scenarioID[0:4] == "demo":
            ctrl.demoMode = True

        ctrl.prepare()
        ctrl.run()

    except KeyboardInterrupt:
        print('\nCancelled by user. Bye!')


if __name__ == '__main__':
    main()