#!/usr/bin/env python3

import logging
import sys
import time
import configparser
import os
import json

this_directory = os.path.dirname(os.path.abspath(__file__))

sys.path.append(this_directory + '../../PythonBaseWrapper/src/logic')
sys.path.append(this_directory + '../../PythonBaseWrapper/src/communication')

from TimeSync import TimeSync
from KafkaConsumer import KafkaConsumer
from KafkaProducer import KafkaProducer

config = configparser.ConfigParser()
config.read('config.properties')
print("HERE", config["general"])
broker = config["general"]["kafkaBroker"]
registry = config["general"]["schemaRegistry"]


class CodipyWrapper:
    """Minimal CoDiPy Wrapper for data consumption and synchronization."""
    
    def __init__(self, scenarioID, instanceID):
        self.regexTopic = ["^provision\.simulation\." + scenarioID + "\.micro\.vehicle"]
        self.topicPre = "provision.simulation." + scenarioID + ".micro" + ".vehicle."
        self.timeTopic = "orchestration.simulation." + scenarioID + ".sync"
        self.scetopic = ['provision.simulation.' + scenarioID + '.scenario']
        self.statusTopic = 'orchestration.simulation.' + scenarioID + '.status'

        self.kid = scenarioID + "." + instanceID
        self.scenarioID = scenarioID
        self.instanceID = instanceID

      ##  self.statusProducer = KafkaProducer(broker, registry, self.kid, useAvro=False)
        self.consumer = None

        self.sce = None
        self.sim = None
        self.timeSync = None
        self.demoMode = False

    def klog(self, msg):
        print("klog:", self.statusTopic, self.instanceID + ": " + msg)
        #self.statusProducer.produce(self.statusTopic, self.instanceID + ": " + msg)

    def prepare(self):
        self.klog("started")

        self.sceConsumer = KafkaConsumer(broker, registry, self.scetopic, self.kid + ".sce")
        self.sce = None
        while self.sce == None:
            try:
                msg = self.sceConsumer.poll(1)
                if msg is not None:
                    print("got scenario configuration", flush=True)
                    self.sce = msg.value()
                else:
                    print("waiting for scenario configuration...", flush=True)
            except Exception as e:
                print("Unexpected error:", e, flush=True)
                time.sleep(1)
                print(".", end='', flush=True)
        self.sceConsumer.stop()
        print("got scenario configuration", flush=True)

        for sim in self.sce['buildingBlocks']:
            if sim['instanceID'] == self.instanceID:
                self.sim = sim
                self.responsibility = sim.get('responsibilities', [])
                self.observers = sim.get('observers', [])
                break

        if self.sim == None:
            print("no simulation instance found for", self.instanceID)
            sys.exit(1)

        self.klog("initialized")

        self.timeSync = TimeSync(broker, registry, self.timeTopic, self.kid + ".time",
                                self.sce['execution']['syncedParticipants'], logging=False,
                                timeoutHandler=self.handleTimeout)

        for p in self.regexTopic:
            self.timeSync.addExpectedPattern(p)

        self.timeSync.joinTiming()
        self.klog("time synchronization started")

    def handleTimeout(self):
        print("handleTimeout", flush=True)
        self.startMainConsumer()

    def startMainConsumer(self):
        if self.consumer is not None:
            self.consumer.stop()
            time.sleep(1)

        if len(self.timeSync.inferedTopics) > 0:
            print("subscribing to inferred topics:", self.timeSync.inferedTopics)
            self.consumer = KafkaConsumer(broker, registry, self.timeSync.inferedTopics, self.kid + "_consumer",
                                         cb=self.processMsg)
        else:
            print("subscribing to regex topics:", self.regexTopic)
            self.consumer = KafkaConsumer(broker, registry, self.regexTopic, self.kid + "_consumer", cb=self.processMsg)

        self.consumer.listenInBG()

    def processMsg(self, inMsg):
        if inMsg != None:
            self.klog("received")
            self.timeSync.notifiyAboutReceivedMessage(inMsg.topic())

    def run(self):
        print("\n\n_______________run_______________\n\n")
        try:
            self.klog("starting consumption")

            stepLengthMs = self.sim.get('stepLength', 1000)
            end = self.sce.get('simulationEnd', 3600000)
            
            self.startMainConsumer()

            iteration = 0
            while self.timeSync.currentLocalTime < end:
                self.timeSync.timeAdvance(stepLengthMs)

                if iteration % 100 == 0:
                    print(f"Step {iteration}, Time: {self.timeSync.currentLocalTime}ms")

                iteration = iteration + 1
                
            self.klog("finished")

        except Exception as e:
            print("main loop caught exception:", e)

        finally:
            if self.consumer is not None:
                self.consumer.stop()
            if self.timeSync is not None:
                self.timeSync.leaveTiming()


def main():
    if len(sys.argv) > 2:
        scenarioID = sys.argv[1]
        instanceID = sys.argv[2]
    else:
        print("non valid data")
        sys.exit(1)
        

    print(f"Starting CoDiPy Wrapper for Co-simulation Framework")
    print(f"Scenario ID: {scenarioID}")
    print(f"Instance ID: {instanceID}")

    try:
        wrapper = CodipyWrapper(scenarioID, instanceID)
        print("Wrapper created successfully")
        

        wrapper.prepare()
        wrapper.run()

    except KeyboardInterrupt:
        print('\nStopped by user. Bye!')
    except Exception as e:
        print(f'Error: {e}')


if __name__ == '__main__':
    main()
