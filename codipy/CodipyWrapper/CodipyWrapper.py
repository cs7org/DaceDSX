#!/usr/bin/env python3

import logging
import sys
import time
import threading
import configparser
import os
import json
from dataclasses import asdict, is_dataclass
from typing import Any, Dict, List, Optional
from collections.abc import Mapping

logger = logging.getLogger(__name__)

this_directory = os.path.dirname(os.path.abspath(__file__))
workspace_root = os.path.dirname(this_directory)

if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

sys.path.append('../../PythonBaseWrapper/src/logic')
sys.path.append('../../PythonBaseWrapper/src/communication')

from TimeSync import TimeSync
from KafkaConsumer import KafkaConsumer
from KafkaProducer import KafkaProducer
from TraCInterface import TraCIInterface

config = configparser.ConfigParser()
config_path = os.path.join(this_directory, 'config.properties')
config.read(config_path)

if not config.sections():
    raise FileNotFoundError(f"Config file not found or empty: {config_path}")

if "general" not in config:
    raise KeyError(f"Missing [general] section in config file: {config_path}")

print(f"Loaded config from: {config_path}")
broker = config["general"]["kafkaBroker"]
registry = config["general"]["schemaRegistry"]


class CodipyWrapper:
    
    def __init__(
        self,
        scenarioID,
        instanceID,
        *,
        step_length_seconds: float = 1.0,
        traci_interface: Optional[TraCIInterface] = None,
    ):
        """
      
        
        """
       # self.regexTopic = ["^provision\.simulation\." + scenarioID + "\.traffic" + "\.micro\.vehicle"]
        self.topicPre = "provision.simulation." + scenarioID + ".traffic.micro.vehicle"
        self.timeTopic = "orchestration.simulation." + scenarioID + ".sync"
        self.scetopic = ['provision.simulation.' + scenarioID + '.scenario']
        self.statusTopic = 'orchestration.simulation.' + scenarioID + '.status'

        self.kid = scenarioID + "." + instanceID
        self.scenarioID = scenarioID
        self.instanceID = instanceID
        self.count_msgs = 0
        self.waitCounter = 0
        self.statusProducer = KafkaProducer(broker, registry, self.kid, useAvro=False)
        self.consumer = None
        self.microMessages: List[Any] = []
        self._micro_lock = threading.Lock()
        self.sce = None
        self.sim = None
        self.timeSync = None
        self.demoMode = False
        self.step_length_seconds = step_length_seconds
        self.stepLengthMs = int(step_length_seconds * 1000)  # Default value, will be overridden from scenario
        self._traci = traci_interface or TraCIInterface(step_length=self.step_length_seconds)
        self.traci = self._traci  

    @property
    def traci_interface(self) -> TraCIInterface:
        """Access the passive TraCI interface."""
        return self._traci

    def klog(self, msg):
       # print("klog:", self.statusTopic, self.instanceID + ": " + msg)
        self.statusProducer.produce(self.statusTopic, self.instanceID + ": " + msg)

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
                
                # Read stepLength from scenario configuration (already in milliseconds)
                if 'stepLength' in sim:
                    self.stepLengthMs = sim['stepLength']
                    print(f"Step length set from scenario config: {self.stepLengthMs}ms", flush=True)
                
                break

        self.sim = self.instanceID

        self.klog("initialized")
        self.klog("waiting for resources")
        
        self.timeSync = TimeSync(broker, registry, self.timeTopic, self.kid + ".time",
                                self.sce['execution']['syncedParticipants'], logging=False,
                                timeoutHandler=self.handleTimeout)

       # for p in self.regexTopic:
        #    self.timeSync.addExpectedPattern(p)

        self.timeSync.joinTiming()
       # self.klog("time synchronization started")

    def handleTimeout(self):
        print("handleTimeout", flush=True)
        self.startMainConsumer()

    def startMainConsumer(self):
        if self.consumer is not None:
            self.consumer.stop()
            time.sleep(1)
            self.waitCounter += 1

        self.consumer = KafkaConsumer(
            broker,
            registry,
            [self.topicPre],
            self.kid + "_consumer",
            cb=self.processMsg,
        )

        self.consumer.listenInBG()

    def processMsg(self, inMsg):
        if inMsg != None:
          #  self.klog("received")
            self.timeSync.notifiyAboutReceivedMessage(inMsg.topic())
            payload = inMsg.value()
            with self._micro_lock:
                self.microMessages.append(payload)

    def run(self):
        print("\n\n_______________run_______________\n\n")
        try:
            self.klog("starting consumption")

            end = self.sce['simulationEnd']

            self.startMainConsumer()

            while self.timeSync.currentLocalTime < end:
                self.timeSync.timeAdvance(self.stepLengthMs)
                drained = self._drain_micro_messages()
                self.count_msgs += len(drained)
                self._push_messages_to_traci(drained)
                print(
                    f"{self.count_msgs} total messages processed | {len(drained)} in this step",
                    flush=True,
                )

            self.klog("finished")

        except Exception as e:
            print("main loop caught exception:", e)

        finally:
            if self.consumer is not None:
                self.consumer.stop()
            if self.timeSync is not None:
                self.timeSync.leaveTiming()

    def _drain_micro_messages(self) -> List[Any]:
        with self._micro_lock:
            drained = self.microMessages
            self.microMessages = []
        return drained

    def _push_messages_to_traci(self, messages: List[Any]) -> None:
        """Process batch of messages and update TraCI interface."""
        current_time = self._current_time_seconds()

        if not messages:
            self._traci.current_time = current_time
            self._traci.simulationStep()
            return

        for message in messages:
            snapshot = self._normalize_micro_message(message, current_time)
            if snapshot is None:
                continue
            if snapshot.get("timestamp") is None:
                snapshot["timestamp"] = current_time
            try:
                self._traci.process_vehicle_message(snapshot)
            except Exception as exc:  
                logger.debug("Failed to process vehicle message %s: %s", snapshot, exc)

        self._traci.simulationStep()

    def _current_time_seconds(self) -> float:
        if self.timeSync is not None and hasattr(self.timeSync, "currentLocalTime"):
            try:
                return float(self.timeSync.currentLocalTime) / 1000.0
            except (TypeError, ValueError):
                pass
        return time.time()

    def start(self) -> None:
     
        self.klog("starting consumption")
        self.end_time = self.sce['simulationEnd']
        self.startMainConsumer()
        print(f"CodipyWrapper started (will run until {self.end_time}ms with {self.stepLengthMs}ms steps)")

    def step(self) -> bool:
        """
        Process one simulation step.
        """
        if not hasattr(self, 'end_time'):
            raise RuntimeError("Must call start() before step()")
        
        if self.timeSync.currentLocalTime >= self.end_time:
            self.klog("finished")
            return False
        
        self.timeSync.timeAdvance(self.stepLengthMs)
        
        drained = self._drain_micro_messages()
        self.count_msgs += len(drained)
        self._push_messages_to_traci(drained)
        
        return True

    def stop(self) -> None:
        print("Stopping CodipyWrapper...")
        try:
            if self.consumer is not None:
                self.consumer.stop()
                print("   Kafka consumer stopped")
        except Exception as e:
            print(f"   Error stopping consumer: {e}")
        
        try:
            if self.timeSync is not None:
                self.timeSync.leaveTiming()
                print("   Left time synchronization")
        except Exception as e:
            print(f"   Error leaving time sync: {e}")

    def _normalize_micro_message(self, message: Any, fallback_timestamp: float) -> Optional[Dict[str, Any]]:
        record = self._as_dict_like(message)
        if record is None:
            logger.debug("Skipping micro message; unable to coerce into dict: %s", message)
            return None

        vehicle_id = record.get("vehicleID") or record.get("vehicle_id")
        if vehicle_id is None:
            logger.debug("Skipping micro message without vehicleID: %s", record)
            return None

        normalized: Dict[str, Any] = {
            "vehicleID": str(vehicle_id),
        }

        # Copy all relevant fields
        for key in (
            "acceleration",
            "angle",
            "edge",
            "lane",
            "positionEdge",
            "route",
            "slope",
            "speed",
            "type",
        ):
            if key in record:
                normalized[key] = record[key]

        position = record.get("position")
        if position is None:
            position = {
                "x": record.get("x"),
                "y": record.get("y"),
                "z": record.get("z"),
            }

        normalized_position = self._normalize_position(position)
        if normalized_position is None:
            logger.debug(
                "Skipping micro message without valid position for vehicle %s: %s",
                vehicle_id,
                record,
            )
            return None

        normalized["position"] = normalized_position

        # Handle timestamp
        timestamp = (
            record.get("timestamp")
            or record.get("time")
            or record.get("simTime")
            or record.get("sim_time")
        )

        if timestamp is not None:
            try:
                timestamp = float(timestamp)
            except (TypeError, ValueError):
                logger.debug(
                    "Unexpected timestamp format for vehicle %s: %s", vehicle_id, record
                )
                timestamp = None

        normalized["timestamp"] = timestamp or fallback_timestamp

        return normalized

    def _normalize_position(self, value: Any) -> Optional[Dict[str, float]]:
        """Normalize position into {x, y, z} dict."""
        if value is None:
            return None

        if isinstance(value, Mapping):
            x = value.get("x")
            y = value.get("y")
            z = value.get("z", 0.0)
            if x is None or y is None:
                return None
            return {
                "x": float(x),
                "y": float(y),
                "z": float(z),
            }

        if isinstance(value, (list, tuple)):
            if len(value) < 2:
                return None
            x, y = value[0], value[1]
            z = value[2] if len(value) > 2 else 0.0
            return {
                "x": float(x),
                "y": float(y),
                "z": float(z),
            }

        # Try to coerce object to dict
        coerced = self._as_dict_like(value)
        if coerced is not None:
            return self._normalize_position(coerced)

        return None

    def _as_dict_like(self, value: Any) -> Optional[Dict[str, Any]]:
        if value is None:
            return None

        if isinstance(value, Mapping):
            return dict(value)

        # Handle bytes/bytearray
        if isinstance(value, (bytes, bytearray)):
            try:
                decoded = value.decode("utf-8")
            except Exception:  # pragma: no cover - defensive
                return None
            return self._as_dict_like(decoded)

        # Handle JSON string
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                return None
            if isinstance(parsed, Mapping):
                return dict(parsed)
            return None

        # Handle dataclass
        if is_dataclass(value):
            return asdict(value)

        # Handle objects with __dict__
        try:
            data = vars(value)
        except TypeError:
            data = None

        if data is not None:
            return {k: v for k, v in data.items() if not k.startswith("_")}

        # Handle namedtuples
        if hasattr(value, "_asdict"):
            try:
                return dict(value._asdict())
            except Exception:
                return None

        return None


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
