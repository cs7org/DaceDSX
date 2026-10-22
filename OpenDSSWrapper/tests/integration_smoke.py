#!/usr/bin/env python3
"""Run the actual Java sender -> SimService -> shell launcher -> Python wrapper.

Build both Java modules first. Run with an existing disposable Kafka/Registry:
  python OpenDSSWrapper/tests/integration_smoke.py --broker localhost:9092 --registry http://localhost:8081
Or use an existing Kafka broker with a minimal test-only registry:
  python OpenDSSWrapper/tests/integration_smoke.py --broker localhost:9092 --test-registry

--test-registry exercises real Kafka clients and Avro serialization, but does not
verify production Schema Registry behaviour. No existing configurations are modified. Logs and
CSV output are retained in the printed temporary work directory.
"""
import argparse
import csv
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]


def test_registry():
    schemas = []
    lock = threading.Lock()

    class Registry(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def respond(self, status, body):
            payload = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/vnd.schemaregistry.v1+json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if urlparse(self.path).path.startswith("/subjects/") and "schema" in body:
                schema = json.dumps(json.loads(body["schema"]), sort_keys=True)
                with lock:
                    if schema not in schemas:
                        schemas.append(schema)
                    schema_id = schemas.index(schema) + 1
                self.respond(200, {"id":schema_id})
            else:
                self.respond(404, {"error_code":40401, "message":"Unsupported test registry operation"})

        def do_GET(self):
            path = unquote(urlparse(self.path).path)
            if path.startswith("/schemas/ids/"):
                with lock:
                    index = int(path.rsplit("/", 1)[1]) - 1
                    if 0 <= index < len(schemas):
                        self.respond(200, {"schema":schemas[index]})
                        return
            self.respond(404, {"error_code":40403, "message":"Schema not found"})

    server = ThreadingHTTPServer(("127.0.0.1", 0), Registry)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--test-registry", action="store_true")
    parser.add_argument("--broker", default="localhost:9092")
    parser.add_argument("--registry", default="http://localhost:8081")
    parser.add_argument("--java", default="java")
    parser.add_argument("--work-dir", type=Path)
    parser.add_argument("--simulation-end", type=int, default=2000)
    args = parser.parse_args()
    if args.simulation_end <= 0 or args.simulation_end % 1000:
        parser.error("--simulation-end must be a positive multiple of 1000 ms")
    work = args.work_dir or Path(tempfile.mkdtemp(prefix="opendss-smoke-"))
    work = work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    print(f"Smoke test logs and results: {work}", flush=True)
    for jar in ("SimService-0.1-jar-with-dependencies.jar", "SendScenarioObject.jar"):
        source = ROOT / "SimService/target" / jar
        if not source.is_file():
            parser.error(f"Build SimService first: {source} is missing")
        shutil.copy2(source, work / jar)
    server = service = None
    try:
        if args.test_registry:
            server = test_registry()
            args.registry = f"http://127.0.0.1:{server.server_port}"
        properties = (ROOT / "SimService/config.properties").read_text().splitlines()
        overrides = {"kafkaBroker":args.broker, "schemaRegistry":args.registry,
            "executablesRoot":str(ROOT / "_data/executables"), "rootDir":str(work),
            "logDir":str(work), "definitionDirectory":str(ROOT / "_data"), "resourceDir":str(work)}
        properties = [line for line in properties if line.split("=",1)[0] not in overrides]
        (work / "config.properties").write_text("\n".join(properties) + "\n" +
            "\n".join(f"{key}={value}" for key,value in overrides.items()) + "\n")
        (work / "wrapper.properties").write_text(
            f"[general]\nkafkaBroker={args.broker}\nschemaRegistry={args.registry}\n"
            f"waitTimeoutSeconds=45\nresultsDirectory={work}/results\n")
        env = {**os.environ, "OPENDSS_PYTHON":sys.executable,
               "OPENDSS_CONFIG":str(work / "wrapper.properties")}
        with (work / "simservice.log").open("w") as service_log:
            service = subprocess.Popen([args.java,"-jar",str(work / "SimService-0.1-jar-with-dependencies.jar")],
                cwd=work, env=env, stdout=service_log, stderr=subprocess.STDOUT, start_new_session=True)
            # SimService starts with auto.offset.reset=latest. Wait until its
            # consumer group has an assignment before publishing a new scenario.
            from confluent_kafka.admin import AdminClient
            from confluent_kafka import ConsumerGroupState
            admin = AdminClient({"bootstrap.servers":args.broker})
            deadline = time.monotonic() + 45
            while time.monotonic() < deadline:
                if service.poll() is not None:
                    raise RuntimeError("SimService exited during startup; see simservice.log")
                groups = admin.list_consumer_groups(request_timeout=5).result().valid
                candidates = [g.group_id for g in groups if g.group_id.startswith("sce")]
                if candidates:
                    descriptions = admin.describe_consumer_groups(candidates, request_timeout=5)
                    if any(future.result().state == ConsumerGroupState.STABLE
                           for future in descriptions.values()):
                        break
                time.sleep(.2)
            else:
                raise TimeoutError("SimService did not subscribe within 45 seconds")
            for fail in (False, True):
                scenario = json.loads((ROOT / "OpenDSSWrapper/example/scenario.json").read_text())
                scenario_id = "smoke_" + uuid4().hex
                scenario["scenarioID"] = scenario_id
                scenario["simulationEnd"] = args.simulation_end
                expected_times = set(range(0, args.simulation_end, 1000))
                if fail:
                    scenario["buildingBlocks"][0]["observers"][0]["filter"] = "nonexistent_bus"
                scenario_path = work / f"{scenario_id}.json"
                scenario_path.write_text(json.dumps(scenario))
                shutil.copy2(ROOT / "OpenDSSWrapper/example/FourBus.dss", work / "FourBus.dss")
                with (work / f"{scenario_id}.sender.log").open("w") as output:
                    result = subprocess.run([args.java, "-jar", str(work / "SendScenarioObject.jar"), str(scenario_path)],
                        cwd=work, env=env, stdout=output, stderr=subprocess.STDOUT, timeout=90)
                expected = 1 if fail else 0
                if result.returncode != expected:
                    raise AssertionError(f"Sender exit {result.returncode}; expected {expected}. See {scenario_id}.sender.log")
                wrapper_log = ROOT / "OpenDSSWrapper/logs" / f"{scenario_id}.opendss0.log"
                shutil.copy2(wrapper_log, work / wrapper_log.name)
                text = wrapper_log.read_text()
                status = "failed" if fail else "finished"
                if f"opendss0: {status}" not in text:
                    raise AssertionError(f"Missing status {status} in wrapper log")
                csv_path = work / "results" / f"opendss_{scenario_id}.opendss0.csv"
                if fail:
                    if csv_path.exists() or "opendss0: finished" in text:
                        raise AssertionError("Failed scenario produced successful results")
                else:
                    with csv_path.open() as stream:
                        rows = list(csv.DictReader(stream))
                    if len(rows) != 4 * len(expected_times) or {int(r["time_ms"]) for r in rows} != expected_times:
                        raise AssertionError("Unexpected observation rows or timestamps")
                    for row in rows:
                        if not .95 < float(row["v_mag_pu"]) < 1.01:
                            raise AssertionError("Unexpected voltage")
                    # Read the real Avro wire records as a separate consumer.
                    sys.path.insert(0, str(ROOT / "OpenDSSWrapper"))
                    from OpenDSSWrapper import KafkaConsumer
                    topic = f"provision.simulation.{scenario_id}.energy.opendss0.bus4"
                    consumer = KafkaConsumer(args.broker, args.registry, [topic],
                        scenario_id + ".verify", strict=True, requestTimeout=10)
                    observations = []
                    deadline = time.monotonic() + 15
                    try:
                        while len(observations) < len(expected_times) and time.monotonic() < deadline:
                            message = consumer.poll(.2)
                            if message is not None:
                                observations.append(message)
                        if len(observations) != len(expected_times):
                            raise AssertionError("Missing Kafka bus observations")
                        import struct
                        times = {struct.unpack("!q", dict(m.headers())["time"])[0] for m in observations}
                        if times != expected_times:
                            raise AssertionError("Incorrect Kafka logical timestamps")
                        if any(abs(float(m.value()["p"]) + 1.8) > .001 for m in observations):
                            raise AssertionError("Incorrect Kafka bus power values")
                    finally:
                        consumer.stop()
                    shutil.copy2(csv_path, work / "results.csv")
                    (work / "summary.json").write_text(json.dumps({
                        "scenario": "OpenDSSWrapper/example/scenario.json",
                        "scenario_id": scenario_id,
                        "snapshots": len(expected_times),
                        "bus_records": len(rows),
                        "time_ms": sorted(expected_times),
                        "kafka_bus4_records_verified": len(observations),
                        "final_bus_results": [r for r in rows if int(r["time_ms"]) == max(expected_times)],
                    }, indent=2) + "\n")
                print(f"PASS: Java submission and automatic launch, {'failure exit' if fail else 'successful CSV'}", flush=True)
            if service.poll() is not None:
                raise AssertionError("SimService exited unexpectedly")
            summary_path = work / "summary.json"
            summary = json.loads(summary_path.read_text())
            summary.update({"execution_mode": "Java SimService / Kafka / OpenDSS",
                            "all_converged": True, "failure_reporting_verified": True})
            summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    finally:
        if service is not None:
            try:
                os.killpg(service.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                service.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(service.pid, signal.SIGKILL)
                service.wait()
            # The service's wrappers belong to the same test-only process group.
            try:
                os.killpg(service.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        if server is not None:
            server.shutdown()
            server.server_close()
    print("Integration smoke test passed", flush=True)


if __name__ == "__main__":
    main()
