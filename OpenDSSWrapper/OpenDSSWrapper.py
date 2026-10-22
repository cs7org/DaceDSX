#!/usr/bin/env python3
"""DaceDSX lifecycle and Kafka communication for OpenDSS."""
import argparse
import configparser
import logging
import math
import os
import re
import signal
import struct
import sys
import tempfile
import time
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse
from urllib.request import url2pathname

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path[:0] = [str(ROOT / "PythonBaseWrapper/src/logic"),
                str(ROOT / "PythonBaseWrapper/src/communication")]
from KafkaConsumer import KafkaConsumer
from KafkaProducer import KafkaProducer
from TimeSync import TimeSync
from OpenDSSApi import OpenDSSAPI

LOG = logging.getLogger("OpenDSSWrapper")


def identifier(value):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise ValueError("Scenario and instance IDs must contain only letters, digits, '_' or '-'")
    return value


class Resources:
    """Match SendScenarioObject ResourceFile records; preserve relative dependencies."""
    def __init__(self, resources, directory):
        self.directory = Path(directory).resolve()
        self.pending = dict(resources)
        self.paths = {}
        networks = [name for name, kind in resources.items() if kind == "Network"]
        if len(networks) != 1:
            raise ValueError("Exactly one Network resource is required")
        self.network = networks[0]
        seen = set()
        for name, kind in resources.items():
            parsed = urlparse(name)
            if parsed.scheme:
                if parsed.scheme != "file" or parsed.netloc not in ("", "localhost"):
                    raise ValueError("Only embedded files and local file:/// references are supported")
                path = Path(url2pathname(parsed.path))
                if not path.is_absolute() or parsed.query or parsed.fragment:
                    raise ValueError("File references must be absolute local paths")
            else:
                path = PurePosixPath(name)
                if path.is_absolute() or ".." in path.parts or "\\" in name or not path.name:
                    raise ValueError(f"Unsafe resource path: {name}")
            key = (path.name, kind)
            if key in seen:
                raise ValueError("Resource basenames and types must be unique (sender uses basename IDs)")
            seen.add(key)

    def accept(self, value):
        for name, kind in list(self.pending.items()):
            parsed = urlparse(name)
            basename = Path(url2pathname(parsed.path)).name
            if value["Type"] != kind or value["ID"] != basename:
                continue
            if parsed.scheme:
                if value["FileReference"] != name:
                    continue
                path = Path(url2pathname(parsed.path)).resolve(strict=True)
            else:
                if value["File"] is None or value["FileReference"] is not None:
                    continue
                path = self.directory / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(bytes(value["File"]))
            if not path.is_file():
                raise ValueError(f"Resource is not a file: {name}")
            self.paths[name] = path
            del self.pending[name]
            return True
        return False


class OpenDSSWrapper:
    def __init__(self, scenario_id, instance_id, config_path=HERE / "config.properties",
                 producer_factory=KafkaProducer, consumer_factory=KafkaConsumer,
                 sync_factory=TimeSync):
        self.scenarioID = identifier(scenario_id)
        self.instanceID = identifier(instance_id)
        config = configparser.ConfigParser()
        if not config.read(config_path):
            raise ValueError(f"Cannot read configuration: {config_path}")
        general = config["general"]
        self.broker = general["kafkaBroker"]
        self.registry = general["schemaRegistry"]
        self.timeout = general.getfloat("waitTimeoutSeconds", fallback=120)
        if not math.isfinite(self.timeout) or self.timeout <= 0:
            raise ValueError("waitTimeoutSeconds must be positive and finite")
        output = Path(general.get("resultsDirectory", "../_data/results"))
        self.output_dir = (Path(config_path).resolve().parent / output).resolve()
        self.producer_factory = producer_factory
        self.consumer_factory = consumer_factory
        self.sync_factory = sync_factory
        self.kid = scenario_id + "." + instance_id
        self.prefix = "provision.simulation." + scenario_id
        self.status_topic = "orchestration.simulation." + scenario_id + ".status"
        self.consumers = []
        self.api = self.sync = self.producer = self.status_producer = None
        self.resource_dir = None
        self.joined = False
        self.pending_inputs = []
        self.input_consumer = None
        self.input_specs = {}
        self.last_input_time = {}

    def consumer(self, suffix):
        result = self.consumer_factory(self.broker, self.registry,
            [self.prefix + "." + suffix], self.kid + "." + suffix, strict=True, requestTimeout=self.timeout)
        self.consumers.append(result)
        return result

    def klog(self, status):
        LOG.info("%s: %s", self.instanceID, status)
        self.status_producer.produce(self.status_topic, self.instanceID + ": " + status)

    def wait_for(self, consumer, predicate, description):
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            message = consumer.poll(min(0.2, max(0, deadline - time.monotonic())))
            if message is not None and predicate(message.value()):
                return message.value()
        raise TimeoutError("Timed out waiting for " + description)

    def prepare(self):
        self.status_producer = self.producer_factory(self.broker, self.registry, self.kid,
            useAvro=False, deliveryTimeout=self.timeout)
        self.klog("started")
        scenario_consumer = self.consumer("scenario")
        self.scenario = self.wait_for(scenario_consumer,
            lambda value: value["scenarioID"] == self.scenarioID, "scenario")
        blocks = [b for b in self.scenario["buildingBlocks"] if b["instanceID"] == self.instanceID]
        if len(blocks) != 1 or blocks[0]["type"] != "OpenDSSWrapper":
            raise ValueError("Scenario must contain exactly one matching OpenDSSWrapper instance")
        self.block = blocks[0]
        self.start = self.scenario["simulationStart"]
        self.end = self.scenario["simulationEnd"]
        self.step_ms = self.block["stepLength"]
        if (any(type(v) is not int for v in (self.start, self.end, self.step_ms))
                or self.start < 0 or self.end <= self.start or self.step_ms <= 0):
            raise ValueError("Require 0 <= simulationStart < simulationEnd and stepLength > 0 (ms)")
        participants = self.scenario["execution"]["syncedParticipants"]
        if type(participants) is not int or participants < 1 or not self.block["synchronized"]:
            raise ValueError("OpenDSS requires synchronization and a positive participant count")
        if self.block["isExternal"]:
            raise ValueError("A SimService-launched wrapper must have isExternal=false")
        for observer in self.block["observers"]:
            if observer["period"] and observer["period"] % self.step_ms:
                raise ValueError("Observer periods must be multiples of stepLength (or zero)")
        self.resource_dir = tempfile.TemporaryDirectory(prefix="opendss-" + self.kid + "-")
        resources = Resources(self.block["resources"], self.resource_dir.name)
        self.klog("waiting for resources")
        resource_consumer = self.consumer("resource")
        self.wait_for(resource_consumer,
            lambda value: resources.accept(value) and not resources.pending, "resources")
        self.api = OpenDSSAPI(resources.paths[resources.network], self.block["parameters"],
            self.block["observers"], self.output_dir / f"opendss_{self.kid}.csv")
        self.api.init(self.block["responsibilities"])
        self.producer = self.producer_factory(self.broker, self.registry, self.kid,
            schemaPath=str(ROOT / "AvroSchemas/bus.avsc"), deliveryTimeout=self.timeout)
        self.sync = self.sync_factory(self.broker, self.registry,
            "orchestration.simulation." + self.scenarioID + ".sync", self.kid + ".time",
            participants, logging=False, waitTimeout=self.timeout, progressHandler=self.receive_inputs)
        for spec in self.api.inputs:
            topic = spec["topic"].replace("{scenarioID}", self.scenarioID)
            if not re.fullmatch(r"[A-Za-z0-9._-]+", topic) or len(topic) > 249:
                raise ValueError(f"Invalid input topic: {topic}")
            if not topic.startswith(self.prefix + ".energy.") or topic.startswith(
                    self.prefix + ".energy." + self.instanceID + "."):
                raise ValueError("Input topics must belong to another instance in this scenario")
            self.input_specs.setdefault(topic, []).append(spec)
            self.sync.addExpectedTopic(topic)
        if self.input_specs:
            self.input_consumer = self.consumer_factory(self.broker, self.registry,
                list(self.input_specs), self.kid + ".inputs", strict=True, requestTimeout=self.timeout)
            self.consumers.append(self.input_consumer)
        self.klog("initialized")
        # Mark before joining, so a partially completed join also sends leave on failure.
        self.joined = True
        self.sync.joinTiming()
        if self.start:
            self.sync.timeAdvance(self.start)

    def receive_inputs(self):
        if self.input_consumer is None:
            return
        # Bounded batch prevents a noisy input from starving synchronization.
        for _ in range(1000):
            message = self.input_consumer.poll(0)
            if message is None:
                break
            topic = message.topic()
            headers = dict(message.headers() or [])
            raw = headers.get("time")
            if not isinstance(raw, bytes) or len(raw) != 8:
                raise ValueError(f"Input on {topic} lacks a DaceDSX logical-time header")
            timestamp = struct.unpack("!q", raw)[0]
            if timestamp < self.start or timestamp < self.last_input_time.get(topic, self.start):
                raise ValueError(f"Stale or out-of-order input on {topic}")
            self.last_input_time[topic] = timestamp
            self.pending_inputs.append((timestamp, topic, message.value()))
            self.sync.notifiyAboutReceivedMessage(topic)

    def run(self):
        self.klog("simulating")
        while self.sync.currentLocalTime < self.end:
            now = self.sync.currentLocalTime
            remaining = []
            # Explicit coupling: data from a previous time is used at this time.
            for timestamp, topic, value in sorted(self.pending_inputs, key=lambda item: item[0]):
                if timestamp < now:
                    for spec in self.input_specs[topic]:
                        self.api.apply_input(spec, value)
                else:
                    remaining.append((timestamp, topic, value))
            self.pending_inputs = remaining
            self.api.solve(now)
            for bus, value in self.api.observations(self.start).items():
                topic = self.prefix + ".energy." + self.instanceID + "." + bus
                if not re.fullmatch(r"[A-Za-z0-9._-]+", topic) or len(topic) > 249:
                    raise ValueError(f"Bus name cannot be used as a Kafka topic: {bus}")
                self.producer.produce(topic, value, timestamp=now)
                self.sync.notifiyAboutSentMessage(topic)
            # Also announces and drains messages from the final simulated interval.
            self.sync.timeAdvance(min(self.step_ms, self.end - now))
        result = self.api.write_results()
        LOG.info("Results saved to %s", result)

    def close(self):
        errors = []
        actions = []
        if self.sync is not None:
            if self.joined:
                actions.append(self.sync.leaveTiming)
            actions.append(self.sync.consumer.stop)
        actions += [consumer.stop for consumer in self.consumers]
        if self.api is not None:
            actions.append(self.api.destroy)
        if self.resource_dir is not None:
            actions.append(self.resource_dir.cleanup)
        for action in actions:
            try:
                action()
            except Exception as exc:
                errors.append(exc)
                LOG.exception("Cleanup failed")
        self.consumers = []
        self.sync = self.api = self.resource_dir = None
        if errors:
            raise RuntimeError("OpenDSS cleanup failed") from errors[0]

    def execute(self):
        try:
            try:
                self.prepare()
                self.run()
            finally:
                self.close()
            self.klog("finished")
        except BaseException:
            if self.status_producer is not None:
                try:
                    self.klog("failed")
                except Exception:
                    LOG.exception("Could not publish failure status")
            raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario_id")
    parser.add_argument("instance_id")
    parser.add_argument("--config", type=Path,
                        default=Path(os.environ.get("OPENDSS_CONFIG", HERE / "config.properties")))
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    def terminated(signum, frame):
        raise InterruptedError(f"Terminated by signal {signum}")
    signal.signal(signal.SIGTERM, terminated)
    try:
        OpenDSSWrapper(args.scenario_id, args.instance_id, args.config).execute()
        return 0
    except (Exception, KeyboardInterrupt):
        LOG.exception("OpenDSS scenario failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
