"""Prepare and start disposable Kafka and Schema Registry with isolated dependencies.

Resolve dependencies: python3 OpenDSSWrapper/tools/local_services.py prepare
Run in Linux/WSL: python3 OpenDSSWrapper/tools/local_services.py start
Stop only the processes started here: python3 OpenDSSWrapper/tools/local_services.py stop
"""
import argparse
import json
import os
from pathlib import Path
from pathlib import PureWindowsPath
import signal
import socket
import subprocess
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "_data/runtime/opendss-services"
CLASSPATH_FILE = RUNTIME / "classpath.txt"


def prepare(maven):
    RUNTIME.mkdir(parents=True, exist_ok=True)
    subprocess.run([maven, "-B", "-Dhttps.protocols=TLSv1.2", "-f",
                    str(Path(__file__).with_name("services-pom.xml")),
                    "dependency:build-classpath", f"-Dmdep.outputFile={CLASSPATH_FILE}"], check=True)


def runtime_classpath():
    source = CLASSPATH_FILE if CLASSPATH_FILE.is_file() else RUNTIME / "classpath.windows.txt"
    if not source.is_file():
        raise RuntimeError("Run local_services.py prepare to resolve Kafka/Registry dependencies.")
    contents = source.read_text().strip()
    if ";" in contents:
        entries = [str(Path("/mnt") / PureWindowsPath(entry).drive[0].lower() /
                       Path(*PureWindowsPath(entry).parts[1:])) for entry in contents.split(";")]
    else:
        entries = contents.split(":")
    if not entries or any(not Path(entry).is_file() for entry in entries):
        raise RuntimeError("Service dependency files are missing; run prepare again.")
    return ":".join(entries)


def available(port):
    with socket.socket() as connection:
        connection.settimeout(.3)
        return connection.connect_ex(("127.0.0.1", port)) == 0


def stop():
    state = RUNTIME / "processes.json"
    if not state.exists():
        return
    processes = json.loads(state.read_text())
    for item in reversed(processes):
        # Avoid acting on a PID reused by an unrelated process.
        command = Path(f"/proc/{item['pid']}/cmdline")
        if command.exists() and str(RUNTIME).encode() in command.read_bytes():
            try:
                os.killpg(item["pid"], signal.SIGTERM)
            except ProcessLookupError:
                continue
            deadline = time.monotonic() + 10
            while command.exists() and str(RUNTIME).encode() in command.read_bytes():
                if time.monotonic() >= deadline:
                    # Only this helper's still-identified process group.
                    try:
                        os.killpg(item["pid"], signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    break
                time.sleep(.2)
    state.unlink()
    print("Stopped the local OpenDSS test services.")


def start():
    classpath = runtime_classpath()
    if any(available(port) for port in (2181, 9092, 8081)):
        raise RuntimeError("Ports 2181, 9092, and 8081 must be free for disposable services.")
    RUNTIME.mkdir(parents=True, exist_ok=True)
    data = RUNTIME / f"run-{time.time_ns()}"
    data.mkdir()
    definitions = [
        ("zookeeper", "org.apache.zookeeper.server.quorum.QuorumPeerMain", 2181,
         f"dataDir={data}/zookeeper-data\nclientPort=2181\nclientPortAddress=127.0.0.1\nadmin.enableServer=false\n"),
        ("kafka", "kafka.Kafka", 9092,
         f"broker.id=0\nlisteners=PLAINTEXT://127.0.0.1:9092\nadvertised.listeners=PLAINTEXT://localhost:9092\n"
         f"log.dirs={data}/kafka-data\nzookeeper.connect=localhost:2181\nnum.partitions=1\n"
         "offsets.topic.replication.factor=1\ntransaction.state.log.replication.factor=1\n"
         "transaction.state.log.min.isr=1\ngroup.initial.rebalance.delay.ms=0\n"
         "auto.create.topics.enable=true\nlog.retention.hours=1\n"),
        ("registry", "io.confluent.kafka.schemaregistry.rest.SchemaRegistryMain", 8081,
         "listeners=http://127.0.0.1:8081\nhost.name=localhost\n"
         "kafkastore.bootstrap.servers=PLAINTEXT://localhost:9092\nkafkastore.topic.replication.factor=1\n"),
    ]
    processes = []
    try:
        for name, main, port, contents in definitions:
            config = RUNTIME / f"{name}.properties"
            config.write_text(contents)
            with (RUNTIME / f"{name}.log").open("w") as log:
                process = subprocess.Popen(["java", "-Xms128m", "-Xmx512m", "-cp", classpath, main, str(config)],
                                           stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            processes.append({"name": name, "pid": process.pid})
            (RUNTIME / "processes.json").write_text(json.dumps(processes, indent=2))
            deadline = time.monotonic() + 45
            while not available(port):
                if process.poll() is not None or time.monotonic() >= deadline:
                    raise RuntimeError(f"{name} did not start; see {RUNTIME / (name + '.log')}")
                time.sleep(.2)
            print(f"Started {name} on localhost:{port}", flush=True)
        with urlopen("http://localhost:8081/subjects", timeout=10) as response:
            print("Schema Registry ready:", response.read().decode(), flush=True)
    except BaseException:
        stop()
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "start", "stop"])
    parser.add_argument("--maven", default="mvn")
    args = parser.parse_args()
    if args.action == "prepare":
        prepare(args.maven)
    elif args.action == "start":
        start()
    else:
        stop()
