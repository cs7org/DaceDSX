import copy
import json
import math
import re
import struct
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import avro.io
import avro.schema

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "OpenDSSWrapper"))
from OpenDSSApi import OpenDSSAPI
from OpenDSSWrapper import OpenDSSWrapper, Resources, main
from KafkaProducer import KafkaProducer
from TimeSync import TimeSync

EXAMPLE = ROOT / "OpenDSSWrapper/example"
SCENARIO = json.loads((EXAMPLE / "scenario.json").read_text())
CIRCUIT = EXAMPLE / "FourBus.dss"


class ElectricalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.api = OpenDSSAPI(CIRCUIT, observers=SCENARIO["buildingBlocks"][0]["observers"],
                              output_path=Path(self.tmp.name) / "results.csv")
        self.api.init(["*"])
        self.addCleanup(self.api.destroy)

    def test_voltage_power_and_units(self):
        self.api.solve(0)
        values = self.api.observations(0)
        self.assertAlmostEqual(float(values["bus4"]["v_mag_pu"]), 0.959956, places=5)
        self.assertAlmostEqual(float(values["bus4"]["v_ang"]), -0.5720325, places=5)
        self.assertAlmostEqual(float(values["bus4"]["p"]), -1.8, places=3)
        self.assertAlmostEqual(float(values["bus4"]["q"]), -0.6, places=3)
        self.assertGreater(float(values["sourcebus"]["p"]), 1.8)
        self.assertEqual(values["sourcebus"]["control"], "Slack")
        self.assertEqual(float(values["bus2"]["p"]), 0)
        self.api.engine.Lines.Name("line1")
        self.assertEqual(self.api.engine.Lines.Units(), 5)  # feet
        for v in values.values():
            self.assertTrue(0.95 < float(v["v_mag_pu"]) < 1.01)

    def test_load_unchanged_and_clock_advances(self):
        for t in (0, 1000, 3600000):
            self.api.solve(t)
            self.api.engine.Loads.Name("load1")
            self.assertEqual(self.api.engine.Loads.kW(), 1800)
            self.assertAlmostEqual(self.api.engine.Solution.DblHour(), t / 3600000)

    def test_profile_uses_milliseconds(self):
        profile = [{"element":"Load.Load1", "points":[
            {"time_ms":1000,"kw":900,"kvar":300},
            {"time_ms":3000,"kw":1200,"kvar":400}]}]
        api = OpenDSSAPI(CIRCUIT, {"load_profiles":json.dumps(profile)})
        self.addCleanup(api.destroy)
        api.init(["*"])
        for t, expected in [(0,1800),(999,1800),(1000,900),(2999,900),(3000,1200)]:
            api.solve(t)
            self.assertEqual(api.engine.Loads.kW(), expected)

    def test_inputs_change_load_and_source(self):
        self.api.apply_input({"element":"Load.Load1","quantity":"power"}, {"p":"-0.9","q":"-0.3"})
        self.api.apply_input({"element":"Vsource.source","quantity":"voltage"},
                             {"v_mag_pu":"1.02","v_ang":"0.1"})
        self.api.solve(1000)
        self.assertEqual(self.api.engine.Loads.kW(), 900)
        self.assertAlmostEqual(self.api.engine.Vsources.PU(), 1.02)
        self.assertAlmostEqual(self.api.engine.Vsources.AngleDeg(), math.degrees(.1))
        self.assertAlmostEqual(float(self.api.get_bus("bus4")["p"]), -.9, places=3)

    def test_observer_filter_period_and_phase(self):
        observer = copy.deepcopy(SCENARIO["buildingBlocks"][0]["observers"][0])
        observer.update(filter="bus4", period=2000)
        api = OpenDSSAPI(CIRCUIT, {"voltage_phase":"2"}, [observer])
        self.addCleanup(api.destroy)
        api.init(["*"])
        api.solve(1000)
        self.assertEqual(api.observations(0), {})
        api.solve(2000)
        self.assertEqual(set(api.observations(0)), {"bus4"})
        self.assertAlmostEqual(float(api.get_bus("bus4")["v_ang"]), -2.6664276, places=4)

    def test_invalid_bus_and_unsolved_output_fail(self):
        with self.assertRaises(RuntimeError):
            self.api.get_bus("bus4")
        self.api.solve(0)
        with self.assertRaises(ValueError):
            self.api.get_bus("missing")

    def test_nonconvergence_cannot_publish_stale_solution(self):
        self.api.solve(0)
        with patch.object(type(self.api.engine.Solution), "Converged", return_value=False):
            with self.assertRaisesRegex(RuntimeError, "did not converge"):
                self.api.solve(1000)
        with self.assertRaises(RuntimeError):
            self.api.get_bus("bus4")

    def test_result_csv_and_write_failure(self):
        self.api.solve(0)
        self.api.observations(0)
        result = self.api.write_results()
        self.assertEqual(len(result.read_text().splitlines()), 5)
        self.assertTrue(result.read_text().startswith("time_ms,name,p,q,v_mag_pu,v_ang,control"))
        self.api.output_path = Path(self.tmp.name)
        with self.assertRaises(OSError):
            self.api.write_results()

    def test_relative_redirects_without_changing_process_directory(self):
        directory = Path(self.tmp.name)
        (directory / "parts").mkdir()
        (directory / "parts/circuit.dss").write_text(CIRCUIT.read_text())
        (directory / "Master.dss").write_text('Redirect "parts/circuit.dss"\n')
        before = Path.cwd()
        api = OpenDSSAPI(directory / "Master.dss")
        self.addCleanup(api.destroy)
        api.init(["*"])
        api.solve(0)
        self.assertEqual(Path.cwd(), before)
        self.assertGreater(float(api.get_bus("bus4")["v_mag_pu"]), .95)


class ResourceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_embedded_main_and_nested_dependency(self):
        resources = Resources({"Master.dss":"Network","parts/Load.dss":"Input"}, self.tmp.name)
        self.assertFalse(resources.accept({"ID":"dummy","Type":"dummy","File":None,"FileReference":None}))
        for name, kind, content in [("Load.dss","Input",b"load"),("Master.dss","Network",b"master")]:
            self.assertTrue(resources.accept({"ID":name,"Type":kind,"File":content,"FileReference":None}))
        self.assertFalse(resources.pending)
        self.assertEqual((Path(self.tmp.name)/"parts/Load.dss").read_bytes(), b"load")

    def test_absolute_file_uri_preserves_root_and_spaces(self):
        path = Path(self.tmp.name) / "circuit file.dss"
        path.write_bytes(b"circuit")
        resources = Resources({path.as_uri():"Network"}, self.tmp.name)
        resources.accept({"ID":path.name,"Type":"Network","File":None,"FileReference":path.as_uri()})
        self.assertEqual(resources.paths[resources.network], path)

    def test_ambiguous_or_unsafe_resources_fail(self):
        for resources in ({"../x":"Network"},{"/x":"Network"},{"s3://bucket/x":"Network"},
                          {"a/x":"Network","b/x":"Network"},{"a":"Input"}):
            with self.subTest(resources=resources), self.assertRaises(ValueError):
                Resources(resources, self.tmp.name)

    def test_scenario_and_results_match_repository_avro_schemas(self):
        source = (ROOT / "JavaBaseWrapper/src/main/java/eu/fau/cs7/daceDS/datamodel/Scenario.java").read_text()
        literal = re.search(r'new org\.apache\.avro\.Schema\.Parser\(\)\.parse\(("(?:\\.|[^"\\])*")\)', source).group(1)
        schema = avro.schema.parse(json.loads(literal))
        self.assertTrue(avro.io.validate(schema, SCENARIO, raise_on_error=True))
        bus_schema = avro.schema.parse((ROOT / "AvroSchemas/bus.avsc").read_text())
        self.assertTrue(avro.io.validate(bus_schema, {key:"0" for key in
            ("name","p","q","v_mag_pu","v_ang","control")}, raise_on_error=True))


class Message:
    def __init__(self, topic, value, timestamp=-1):
        self._topic, self._value, self._timestamp = topic, value, timestamp
    def topic(self): return self._topic
    def value(self): return self._value
    def headers(self): return [("time", struct.pack("!q", self._timestamp))]


class Bus:
    def __init__(self):
        self.records = []
        self.consumers = []
        self.lock = threading.Lock()
    def producer(self, *args, **kwargs):
        bus = self
        class Producer:
            def produce(self, topic, value, key="empty", timestamp=-1):
                with bus.lock:
                    bus.records.append(Message(topic, value, timestamp))
        return Producer()
    def consumer(self, broker, registry, topics, consumerID, **kwargs):
        bus = self
        class Consumer:
            def __init__(self): self.offset = 0; self.closed = False
            def poll(self, timeout):
                with bus.lock:
                    while self.offset < len(bus.records):
                        msg = bus.records[self.offset]
                        self.offset += 1
                        if msg.topic() in topics:
                            return msg
                if timeout: time.sleep(min(timeout, .001))
                return None
            def stop(self): self.closed = True
        result = Consumer()
        self.consumers.append(result)
        return result


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.config = Path(self.tmp.name) / "config.properties"
        self.config.write_text("[general]\nkafkaBroker=unused\nschemaRegistry=unused\nwaitTimeoutSeconds=2\nresultsDirectory=results\n")
        self.bus = Bus()
        self.scenario = copy.deepcopy(SCENARIO)
        self.scenario["scenarioID"] = "test"
        self.scenario["simulationEnd"] = 3000
        self.addCleanup(patch.stopall)
        patch("TimeSync.KafkaProducer", self.bus.producer).start()
        patch("TimeSync.KafkaConsumer", self.bus.consumer).start()

    def wrapper(self, instance="opendss0"):
        return OpenDSSWrapper("test", instance, self.config,
            producer_factory=self.bus.producer, consumer_factory=self.bus.consumer)

    def submit(self):
        p = self.bus.producer()
        p.produce("provision.simulation.test.scenario", self.scenario)
        p.produce("provision.simulation.test.resource", {"ID":"FourBus.dss", "Type":"Network",
                   "File":CIRCUIT.read_bytes(), "FileReference":None})

    def statuses(self):
        return [msg.value() for msg in self.bus.records if msg.topic().endswith(".status")]

    def test_complete_run_timestamps_counts_results_and_cleanup(self):
        self.submit()
        self.wrapper().execute()
        records = [msg for msg in self.bus.records if ".energy." in msg.topic()]
        self.assertEqual(len(records), 12)
        self.assertEqual({m._timestamp for m in records}, {0,1000,2000})
        requests = [m.value() for m in self.bus.records if m.topic().endswith(".sync") and m.value()["Action"] == "request"]
        self.assertEqual([m["Time"] for m in requests], [1000,2000,3000])
        self.assertEqual([sum(m["Messages"].values()) for m in requests], [4,4,4])
        self.assertEqual(self.statuses()[-1], "opendss0: finished")
        self.assertTrue((Path(self.tmp.name)/"results/opendss_test.opendss0.csv").is_file())
        self.assertTrue(all(c.closed for c in self.bus.consumers))

    def test_nonzero_start_and_partial_final_interval(self):
        self.scenario.update(simulationStart=5000, simulationEnd=6500)
        self.submit()
        self.wrapper().execute()
        records = [m for m in self.bus.records if ".energy." in m.topic()]
        self.assertEqual({m._timestamp for m in records}, {5000,6000})

    def test_solver_or_disk_failure_never_reports_finished(self):
        for method in ("solve", "write_results"):
            with self.subTest(method=method):
                self.bus.records.clear()
                self.submit()
                with patch.object(OpenDSSAPI, method, side_effect=RuntimeError("forced failure")):
                    with self.assertRaises(RuntimeError):
                        self.wrapper().execute()
                self.assertEqual(self.statuses()[-1], "opendss0: failed")
                self.assertNotIn("opendss0: finished", self.statuses())
                self.assertTrue(all(c.closed for c in self.bus.consumers))

    def test_missing_resource_and_missing_participant_timeout(self):
        self.config.write_text(self.config.read_text().replace("=2\n", "=0.02\n"))
        self.bus.producer().produce("provision.simulation.test.scenario", self.scenario)
        with self.assertRaises(TimeoutError): self.wrapper().execute()
        self.bus.records.clear()
        self.scenario["execution"]["syncedParticipants"] = 2
        self.submit()
        with self.assertRaises(TimeoutError): self.wrapper().execute()
        self.assertTrue(all(c.closed for c in self.bus.consumers))

    def test_two_instances_apply_previous_step_input(self):
        second = copy.deepcopy(self.scenario["buildingBlocks"][0])
        second["instanceID"] = "opendss1"
        second["parameters"] = {"inputs":json.dumps([{"topic":"provision.simulation.{scenarioID}.energy.opendss0.bus4",
            "element":"Load.Load1","quantity":"power"}])}
        self.scenario["buildingBlocks"].append(second)
        self.scenario["execution"]["syncedParticipants"] = 2
        self.scenario["buildingBlocks"][0]["parameters"] = {"load_profiles":json.dumps([
            {"element":"Load.Load1", "points":[{"time_ms":0,"kw":900,"kvar":300}]}])}
        self.submit()
        errors = []
        def run(instance):
            try: self.wrapper(instance).execute()
            except BaseException as exc: errors.append(exc)
        threads = [threading.Thread(target=run, args=(name,)) for name in ("opendss0","opendss1")]
        for thread in threads: thread.start()
        for thread in threads: thread.join(5)
        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertEqual(errors, [])
        powers = {m._timestamp:float(m.value()["p"]) for m in self.bus.records
                  if m.topic() == "provision.simulation.test.energy.opendss1.bus4"}
        self.assertAlmostEqual(powers[0], -1.8, places=3)
        self.assertAlmostEqual(powers[1000], -.9, places=3)
        self.assertAlmostEqual(powers[2000], -.9, places=3)

    def test_time_grant_and_message_count_waits_are_bounded(self):
        self.config.write_text(self.config.read_text().replace("=2\n", "=0.02\n"))
        self.submit()
        wrapper = self.wrapper()
        wrapper.prepare()
        try:
            wrapper.sync.participants["stalled"] = 0
            with self.assertRaisesRegex(TimeoutError, "time grant"):
                wrapper.sync.timeAdvance(1000)
            del wrapper.sync.participants["stalled"]
            wrapper.sync.refreshLBTS()
            wrapper.sync.expectedReceiveCount["missing"] = 1
            with self.assertRaisesRegex(TimeoutError, "announced messages"):
                wrapper.sync.timeAdvance(1000)
        finally:
            wrapper.close()

    def test_cli_returns_failure(self):
        with patch.object(OpenDSSWrapper, "execute", side_effect=RuntimeError("failure")):
            with self.assertLogs("OpenDSSWrapper", level="ERROR"):
                self.assertEqual(main(["test", "opendss0", "--config", str(self.config)]), 1)


class TransportTests(unittest.TestCase):
    def test_new_topics_can_appear_after_subscription(self):
        from KafkaConsumer import KafkaConsumer
        from confluent_kafka import KafkaError
        consumer = KafkaConsumer.__new__(KafkaConsumer)
        consumer.strict = True
        consumer.consumer = Mock()
        message = Mock()
        message.error.return_value = KafkaError(KafkaError.UNKNOWN_TOPIC_OR_PART)
        consumer.consumer.poll.return_value = message
        self.assertIsNone(consumer.poll(.1))
        message.error.return_value = None
        self.assertIs(consumer.poll(.1), message)
        message.error.return_value = KafkaError(KafkaError.TOPIC_AUTHORIZATION_FAILED)
        with self.assertRaises(RuntimeError):
            consumer.poll(.1)

    def test_failed_delivery_raises(self):
        producer = KafkaProducer.__new__(KafkaProducer)
        producer.producerID = "test"
        producer.deliveryTimeout = 1
        class Backend:
            def produce(self, **kwargs): kwargs["on_delivery"]("broken", None)
            def flush(self, timeout): return 0
        producer.producer = Backend()
        with self.assertRaisesRegex(RuntimeError, "delivery failed"):
            producer.produce("topic", "value", timestamp=1000)

    def test_registry_http_requests_have_a_deadline(self):
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        from AvroProducerConsumer import create_schema_registry
        import requests
        class SlowHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                time.sleep(.1)
            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), SlowHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            client = create_schema_registry({"url":f"http://127.0.0.1:{server.server_port}",
                                             "request.timeout":.02})
            with self.assertRaises(requests.exceptions.Timeout):
                client._send_request(f"http://127.0.0.1:{server.server_port}/schemas/ids/1")
        finally:
            server.shutdown()
            server.server_close()

    def test_timesync_counts_all_new_pattern_topics(self):
        sync = TimeSync.__new__(TimeSync)
        sync.participants = {"peer":0}
        sync.expectedReceiveCount = {}
        sync.expectedPattern = [re.compile("^data\\.")]
        sync.inferedTopics = []
        sync.logging = False
        sync.processSyncMsg({"Sender":"peer", "Action":"request", "Time":1000,
                             "Messages":{"data.one":1,"data.two":2}})
        self.assertEqual(sync.expectedReceiveCount, {"data.one":1,"data.two":2})

    @unittest.skipIf(sys.platform == "win32", "Bash launchers are tested in Linux/WSL")
    def test_launchers_work_from_unrelated_directory_and_preserve_exit_code(self):
        import os
        with tempfile.TemporaryDirectory(prefix="wrapper test ") as directory:
            fake = Path(directory) / "python"
            fake.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\nexit 7\n')
            fake.chmod(0o755)
            for script in (ROOT/"OpenDSSWrapper/run.sh", ROOT/"_data/executables/OpenDSSWrapper/run.sh"):
                result = subprocess.run([str(script),"testlauncher","opendss0"],cwd=directory,
                    env={**os.environ,"OPENDSS_PYTHON":str(fake)}, capture_output=True)
                self.assertEqual(result.returncode, 7, result.stderr)
            log = ROOT/"OpenDSSWrapper/logs/testlauncher.opendss0.log"
            self.assertIn(str(ROOT/"OpenDSSWrapper/OpenDSSWrapper.py"), log.read_text())
            log.unlink()


if __name__ == "__main__":
    unittest.main()
