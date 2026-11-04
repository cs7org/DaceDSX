# OpenDSS in DaceDSX

This wrapper runs a complete OpenDSS circuit as synchronized, quasi-static
snapshots. SimService starts it when a building block has
`"type": "OpenDSSWrapper"`. It uses the shared Kafka and TimeSync classes from
`PythonBaseWrapper`.

## Install and build

Use Linux or WSL, Python 3.10+ and a JDK (11+), with Maven on PATH.
From the repository root:

```bash
python3 -m venv OpenDSSWrapper/.venv-linux
OpenDSSWrapper/.venv-linux/bin/python -m pip install -r OpenDSSWrapper/requirements.txt
mvn -f JavaBaseWrapper/pom.xml install
mvn -f SimService/pom.xml package
cp SimService/config.properties SimService/target/config.properties
```

`OpenDSSDirect.py` includes its DSS engine; a separate Windows OpenDSS installation
is unnecessary. The Python requirements include the dependencies used by the
repository's legacy Confluent Avro serializer. `target/` is build output and is
not committed to Git.

For direct execution on Windows, create a separate native environment:

```powershell
python -m venv OpenDSSWrapper/.venv
.\OpenDSSWrapper\.venv\Scripts\python.exe -m pip install -r OpenDSSWrapper/requirements.txt
.\OpenDSSWrapper\.venv\Scripts\python.exe OpenDSSWrapper/run_local.py OpenDSSWrapper/example/scenario.json
```

This runs the bundled, uncoupled scenario with the actual OpenDSS engine and
writes `results.csv` and `summary.json` under `_data/results/opendss_four_bus_local`.
Use `--output-dir PATH` to choose another output directory. External participant
inputs require the synchronized Kafka execution below. The Bash launcher prefers
`.venv-linux`; `OPENDSS_PYTHON` overrides the interpreter selection.

Start Kafka and Schema Registry using the repository's root installation guide.
Edit **SimService/target/config.properties** for your machine. In particular:

```properties
kafkaBroker=localhost:9092
schemaRegistry=http://localhost:8081
executablesRoot=/ABSOLUTE/PATH/DaceDSX/_data/executables
rootDir=/ABSOLUTE/PATH/DaceDSX/_data
logDir=/ABSOLUTE/PATH/DaceDSX/_data
resourceDir=/ABSOLUTE/PATH/DaceDSX/SimService
definitionDirectory=/ABSOLUTE/PATH/DaceDSX/_data
```

Use an absolute checkout path without spaces: the existing SimService process
launcher splits its command string on whitespace. Keep the topic settings from
the template. The Kafka broker address must **not** start with `http://`.
Also configure **OpenDSSWrapper/config.properties** with the same broker and
registry. Its result path is relative to that configuration file.

## Submit the bundled scenario

From the repository root, in terminal 1:

```bash
java -jar SimService/target/SimService-0.1-jar-with-dependencies.jar
```

In terminal 2:

```bash
java -jar SimService/target/SendScenarioObject.jar OpenDSSWrapper/example/scenario.json
```

The empty `scenarioID` lets SendScenarioObject generate an ID; use a new ID for
every run because Kafka retains old messages. The sender publishes the scenario,
SimService launches `_data/executables/OpenDSSWrapper/run.sh`, and the sender
publishes resource bytes after receiving SimService's acknowledgement. The
launcher forwards to `OpenDSSWrapper/run.sh`, which starts Python in the foreground
and preserves its exit code. No graphical terminal is needed. SimService can
terminate that process directly; this wrapper spawns no child simulator that
needs a separate `kill.sh`.

The sample has one synchronized participant and ten snapshots at 0, 1000, ...,
9000 ms. `simulationEnd` is exclusive. Expected outputs:

- Log: `OpenDSSWrapper/logs/<scenarioID>.opendss0.log`.
- CSV: `_data/results/opendss_<scenarioID>.opendss0.csv`, 40 data rows.
- Avro bus records: `provision.simulation.<scenarioID>.energy.opendss0.<bus>`.
- Lifecycle messages: `orchestration.simulation.<scenarioID>.status`.

The synthetic **FourBus.dss** circuit is a demonstration, **not an IEEE reference
feeder**. It has a 1.8 MW / 0.6 Mvar load, explicit ohm/kft line-code units,
and a receiving-bus voltage of approximately **0.959956 p.u.** at the original
loading. Source injection is approximately 1.842 MW / 0.713 Mvar. Small numerical
variation is expected. A converged solution alone does not establish that a
user-supplied electrical model is physically appropriate.

`finished` is published only after simulation, CSV writing and cleanup succeed.
On failure, the wrapper reports `failed`, logs the traceback and returns a nonzero
exit code; SendScenarioObject also returns nonzero after receiving that status.
Scenario, resource, synchronization, delivery and registry waits have configured
deadlines. `waitTimeoutSeconds` defaults to 120; increase it for slow participants.

For manual diagnostics, after the scenario/resources have been submitted:

```bash
OpenDSSWrapper/run.sh SCENARIO_ID opendss0
```

Do not start a duplicate instance alongside the one SimService launched.
`OPENDSS_PYTHON` may specify an absolute interpreter path; `OPENDSS_CONFIG` or
`--config FILE` can select another configuration.

## Resources and scenario fields

The example contains every required field in the repository's Scenario Avro
schema. `syncedParticipants` is an integer count of TimeSync participants;
`parameters` is a map of **strings**, including any JSON encoded inside it.
`stepLength`, simulation bounds and observer `period` are in milliseconds.

Declare exactly one `Network` resource (the master DSS file). Relative resource
names are resolved by the sender against the scenario's directory and sent as
bytes. List every dependency explicitly, for example:

```json
"resources": {
  "Master.dss": "Network",
  "parts/Loads.dss": "Input",
  "profiles/demand.csv": "Input"
}
```

The receiver recreates these relative paths in a private temporary directory
before compiling the network. Basename/type pairs must be unique because the
Java sender identifies files by basename. Keep `Redirect` and data paths relative
to the master file. Alternatively, use an absolute `file:///.../Master.dss` URI;
that file and its dependencies must exist on the **wrapper host**, with the same
paths. Remote URI schemes, traversal paths and ambiguous resource names fail
explicitly. Do not mix embedded dependencies with a master file in an unrelated
file-reference directory.

## Electrical and timing contract

The existing `AvroSchemas/bus.avsc` represents one scalar voltage per bus:

| Field | Meaning |
| --- | --- |
| `name` | OpenDSS bus name, lower case |
| `v_mag_pu` | Phase-to-neutral voltage magnitude in per unit |
| `v_ang` | That phase's angle in radians |
| `p`, `q` | Net injection from enabled power-conversion elements at the bus, MW/Mvar; generation positive and consumption negative |
| `control` | `Slack` if an enabled voltage source is connected; otherwise `PQ` |

All six fields are strings, as required by the existing Avro schema. The selected
voltage phase defaults to node 1; set `"voltage_phase": "2"` or `"3"` to select
another. Missing phases or voltage bases cause an error. Power is summed across
all conductors of the attached PC-element terminals. A junction with no such
elements has zero net injection; that is **not** its line or transformer through-flow.
The scalar record is not a full three-phase measurement and `control` does not
classify generator regulation modes.

Only `publish`/`bus` observers with `type: "avro"` and an empty `trigger` are
supported. The filter is `*` or a comma-separated bus list. Period zero publishes
every step; a positive period must be a multiple of `stepLength` and is anchored
to `simulationStart`. Empty observers produce no bus records. Responsibilities
must be `["*"]`; automatic circuit partitioning is not implemented.

At each tick the wrapper applies inputs from earlier ticks, sets the OpenDSS
clock, solves, publishes observations with a DaceDSX `time` header, announces
message counts, and waits for the next time grant. The final grant drains the
last interval's announced messages. This is explicit coupling with a one-step
input delay for equal step lengths, not an iterative boundary power-flow solver.

No loads change automatically. To use a piecewise-constant load profile, encode
this JSON array as the string value of the `load_profiles` parameter:

```json
[{"element":"Load.Load1","points":[
  {"time_ms":0,"kw":1800,"kvar":600},
  {"time_ms":5000,"kw":900,"kvar":300}
]}]
```

Before its first profile point, a load retains its circuit setting. For external
inputs, encode this array as the string value of `inputs`:

```json
[{"topic":"provision.simulation.{scenarioID}.energy.other.bus4",
  "element":"Load.Load1","quantity":"power"}]
```

`{scenarioID}` is expanded at runtime. A `power` input reads the bus record's net
injection in MW/Mvar and sets `Load.kW = -1000*p`, `Load.kvar = -1000*q`.
A `voltage` input targets an existing `Vsource`, using positive `v_mag_pu` and
`v_ang` in radians. Initial conditions come from the circuit. One writer per
element is allowed; non-finite values and out-of-order timestamps are rejected.

The sending participant must publish the bus Avro schema with an eight-byte
big-endian logical `time` header and announce exact-topic message counts through
TimeSync. Use compatible step lengths and time bounds. Connecting a PyPSA topic
also requires choosing electrically meaningful boundaries and matching its
coupling algorithm; sharing a schema does not make arbitrary circuits compatible.
Dynamic/transient simulation modes are outside this adapter's scope.

## Tests

```bash
OpenDSSWrapper/.venv-linux/bin/python -m unittest discover -s OpenDSSWrapper/tests -v
```

The tests run the actual OpenDSS engine, validate the example against the Java
Scenario schema, exercise resource delivery, failure paths, timestamps and
message counts, and couple two wrapper instances through an in-memory transport.
They do not require Kafka. For the Java/Kafka smoke test, see the command and
options in `tests/integration_smoke.py`.

To exercise the Java submission path against a disposable Kafka/Schema Registry:

```bash
OpenDSSWrapper/.venv-linux/bin/python OpenDSSWrapper/tests/integration_smoke.py \
  --broker localhost:9092 --registry http://localhost:8081 \
  --simulation-end 10000 --work-dir _data/results/opendss_full_run
```

The smoke test starts the actual SimService and SendScenarioObject JARs, verifies
successful automatic launch, CSV rows, decoded Kafka bus records and logical
timestamps, then submits an invalid bus filter and checks failure reporting and
the sender's nonzero exit code. It retains logs in the printed work directory,
copies the successful CSV to `results.csv`, and writes `summary.json`. Its default
duration is two snapshots; `--simulation-end 10000` runs all ten example snapshots.

For disposable local services in WSL/Linux, without Docker, use a JDK (17+)
and Maven:

```bash
python3 OpenDSSWrapper/tools/local_services.py prepare
python3 OpenDSSWrapper/tools/local_services.py start
# Run integration_smoke.py using the command above.
python3 OpenDSSWrapper/tools/local_services.py stop
```

The helper resolves an isolated Kafka/Schema Registry classpath from
`tools/services-pom.xml`, stores service data under `_data/runtime`, and uses
ports 2181, 9092 and 8081 on localhost. These ports must be available. `stop`
terminates only the service processes recorded by this helper. An existing
Windows Maven classpath is also accepted when running services in WSL.

Validation of this change: 25 automated tests passed in WSL with Python 3.12;
Windows passed 24 tests with its Bash-only test skipped. Both Maven builds passed
with JDK 17. The full ten-snapshot integration test passed using real Confluent
Kafka `6.1.1-ccs` and Schema Registry `6.1.1` on Java 21. The two-instance input
test uses an in-memory transport; an electrical co-simulation with PyPSA still
requires a separate model-specific validation.
