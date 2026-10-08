# Run an OpenDSS scenario

The `OpenDSSDirect.py` dependency includes the DSS engine. Install the pinned
wrapper requirements in a Python environment; no separate OpenDSS installation
is required.

From the repository root on Windows:

```powershell
python -m venv OpenDSSWrapper/.venv
.\OpenDSSWrapper\.venv\Scripts\python.exe -m pip install -r OpenDSSWrapper/requirements.txt
.\OpenDSSWrapper\.venv\Scripts\python.exe OpenDSSWrapper/run_local.py OpenDSSWrapper/example/scenario.json
```

Results are written to `_data/results/opendss_four_bus_local/results.csv` and
`summary.json`. The example runs ten snapshots, at 0 through 9000 milliseconds.

For synchronized execution through SimService and Kafka, use Linux/WSL and
follow [the OpenDSS wrapper guide](OpenDSSWrapper/README.md). It includes Java
builds, disposable Kafka/Schema Registry setup, scenario submission and an
end-to-end validation command.
