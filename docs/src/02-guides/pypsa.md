# Running PyPSA scenarios



## Running PyPSA scenarios

1. **Install Python**: [Download Python](https://www.python.org/downloads/) and set it up.
2. **Install PyPSA**: Follow the [installation guide](https://pypsa-eur.readthedocs.io/en/latest/installation.html).
3. **Install Required Python Packages**:
   ```bash
   pip install confluent-kafka[avro] avro tables
   ```
4. Create a scenario file and place it in `_data/scenarios`.
5. Follow the general instructions in the **"What to do to run a Scenario in DaceDSX"** section.

For the uncoupled `minimal_network.json` example, a local runner is also available.
It reads the scenario and uses `PyPSAAPI` directly, without Kafka or SimService.
Use Python 3.10 or newer to create the environment (this example was tested
with Python 3.12). Run these commands from the repository root on Windows:

```powershell
python -m venv .venv-pypsa
.\.venv-pypsa\Scripts\python.exe -m pip install -r PyPSAWrapper\requirements-local.txt
.\.venv-pypsa\Script# Introduction
s\python.exe PyPSAWrapper\run_local.py _data\scenarios\minimal_network.json
```

Results are saved in `_data/results/minimal_network/`: `powerflow_results.xlsx`
contains bus voltages and line flows for both snapshots; CSV files and
`summary.json` include numerical results and convergence diagnostics.
The example covers 0 to 2 milliseconds with a 1 millisecond step.
The local runner supports a single uncoupled network; coupled scenarios use
the Kafka orchestration instructions above.


