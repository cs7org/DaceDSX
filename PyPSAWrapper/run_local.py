"""Run a single, uncoupled PyPSA scenario without the Kafka orchestration service.

From the repository root:
    .venv-pypsa/Scripts/python.exe PyPSAWrapper/run_local.py _data/scenarios/minimal_network.json
"""

import argparse
import hashlib
import json
import logging
import math
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pypsa

from PyPSAApi import PyPSAAPI


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    scenario_path = args.scenario.resolve()
    scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
    blocks = scenario["buildingBlocks"]
    if (len(blocks) != 1 or blocks[0]["type"] != "PyPSAWrapper"
            or scenario.get("translators") or scenario.get("projectors")):
        raise ValueError("Local execution requires one uncoupled PyPSAWrapper.")
    block = blocks[0]
    if block.get("parameters", {}).get("copy_buses") or block.get("responsibilities") not in (None, [], ["*"]):
        raise ValueError("Partitioned networks require the Kafka co-simulation runner.")
    start, end, step = (scenario["simulationStart"], scenario["simulationEnd"], block["stepLength"])
    if step <= 0 or end <= start:
        raise ValueError("The scenario must have positive duration and stepLength.")
    steps = (end - start) / step
    if not math.isclose(steps, round(steps)):
        raise ValueError("The duration must be a whole number of simulation steps.")
    steps = round(steps)
    resources = [name for name, kind in block["resources"].items() if kind.lower() == "network"]
    if len(resources) != 1:
        raise ValueError("Exactly one network resource is required.")
    resource = resources[0]
    if resource.startswith("file:///"):
        resource = resource[len("file:///"):]
    network_path = Path(resource)
    if not network_path.is_absolute():
        # DaceDSX resources are resolved from the wrapper's working directory.
        network_path = Path(__file__).resolve().parent / network_path
    network_path = network_path.resolve(strict=True)
    # Uncoupled execution needs no Kafka consumer, producer, or time synchronizer.
    api = PyPSAAPI(str(network_path), None, None, None, scenario["scenarioID"], [],
                   block["instanceID"], step_length=step / 1000, simulationEnd=steps,
                   parameters=block.get("parameters", {}))
    api.init(block.get("responsibilities", []))
    network = api.network
    snapshots = network.snapshots
    diagnostics = []
    for iteration, snapshot in enumerate(snapshots):
        api.prepareStep(iteration)
        result = api.step(iteration)
        api.processStep(iteration)
        api.postStep(iteration, start + (iteration + 1) * step)
        for subnetwork in result["converged"].columns:
            diagnostics.append({
                "step": iteration + 1,
                "simulation_time_ms": start + (iteration + 1) * step,
                "snapshot": str(snapshot),
                "subnetwork": str(subnetwork),
                "converged": bool(result["converged"].loc[snapshot, subnetwork]),
                "iterations": int(result["n_iter"].loc[snapshot, subnetwork]),
                "error": float(result["error"].loc[snapshot, subnetwork]),
            })
    convergence = pd.DataFrame(diagnostics)
    if convergence.empty or not convergence["converged"].all():
        raise RuntimeError(f"Power flow did not converge:\n{convergence.to_string(index=False)}")
    voltages = network.buses_t.v_mag_pu.loc[snapshots]
    if not np.isfinite(voltages.to_numpy()).all():
        raise RuntimeError("Power flow produced non-finite bus voltages.")
    output = args.output_dir or Path(__file__).resolve().parents[1] / "_data" / "results" / scenario_path.stem
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    workbook = api.write_results(output / "powerflow_results.xlsx")
    convergence.to_csv(output / "convergence.csv", index=False)
    for component, attributes in (
        ("buses", ("v_mag_pu", "v_ang", "p", "q")),
        ("lines", ("p0", "q0", "p1", "q1")),
        ("transformers", ("p0", "q0", "p1", "q1")),
        ("generators", ("p", "q")),
        ("loads", ("p", "q")),
    ):
        for attribute in attributes:
            frame = getattr(network, component + "_t")[attribute].loc[snapshots]
            if not frame.empty:
                frame.to_csv(output / f"{component}_{attribute}.csv")
    summary = {
        "scenario_id": scenario["scenarioID"],
        "instance_id": block["instanceID"],
        "execution_mode": "standalone PyPSA power flow (without Kafka)",
        "wrapper_api": "PyPSAApi.PyPSAAPI",
        "scenario_path": str(scenario_path),
        "network_path": str(network_path),
        "network_sha256": hashlib.sha256(network_path.read_bytes()).hexdigest(),
        "python_version": sys.version.split()[0],
        "pypsa_version": pypsa.__version__,
        "simulation_start_ms": start,
        "simulation_end_ms": end,
        "step_length_ms": step,
        "steps": steps,
        "snapshots": [str(snapshot) for snapshot in snapshots],
        "buses": len(network.buses),
        "lines": len(network.lines),
        "generators": len(network.generators),
        "loads": len(network.loads),
        "all_converged": True,
        "max_power_flow_error": float(convergence["error"].max()),
        "min_bus_voltage_pu": float(voltages.min().min()),
        "max_bus_voltage_pu": float(voltages.max().max()),
        "output_directory": str(output),
        "workbook": str(workbook),
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
