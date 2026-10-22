"""Execute a single uncoupled OpenDSS scenario directly, without Kafka."""
import argparse
import json
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname

from OpenDSSApi import OpenDSSAPI


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    scenario_path = args.scenario.resolve(strict=True)
    scenario = json.loads(scenario_path.read_text())
    blocks = scenario["buildingBlocks"]
    if len(blocks) != 1 or blocks[0]["type"] != "OpenDSSWrapper" or scenario["translators"] or scenario["projectors"]:
        raise ValueError("Local execution requires one uncoupled OpenDSSWrapper.")
    block = blocks[0]
    if json.loads(block["parameters"].get("inputs", "[]")):
        raise ValueError("External inputs require the Kafka orchestration runner.")
    start, end, step = scenario["simulationStart"], scenario["simulationEnd"], block["stepLength"]
    if any(type(v) is not int for v in (start, end, step)) or start < 0 or end <= start or step <= 0:
        raise ValueError("Require 0 <= simulationStart < simulationEnd and positive stepLength.")
    if any(observer["period"] and observer["period"] % step for observer in block["observers"]):
        raise ValueError("Observer periods must be multiples of stepLength (or zero).")
    networks = [name for name, kind in block["resources"].items() if kind == "Network"]
    if len(networks) != 1:
        raise ValueError("Exactly one Network resource is required.")
    resource = urlparse(networks[0])
    if resource.scheme and (resource.scheme != "file" or resource.netloc not in ("", "localhost")):
        raise ValueError("Only local circuit resources are supported.")
    circuit = Path(url2pathname(resource.path)) if resource.scheme else scenario_path.parent / networks[0]
    output = (args.output_dir or Path(__file__).resolve().parents[1] / "_data/results/opendss_four_bus_local").resolve()
    output.mkdir(parents=True, exist_ok=True)
    api = OpenDSSAPI(circuit, block["parameters"], block["observers"], output / "results.csv")
    try:
        api.init(block["responsibilities"])
        times = list(range(start, end, step))
        for time_ms in times:
            api.solve(time_ms)
            api.observations(start)
        result = api.write_results()
        summary = {"execution_mode": "standalone OpenDSS engine", "scenario": str(scenario_path),
                   "steps": len(times), "time_ms": times, "all_converged": True,
                   "result_rows": len(api.results), "results_file": str(result),
                   "final_bus_results": [row for row in api.results if row["time_ms"] == times[-1]]}
        (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        print(json.dumps(summary, indent=2))
    finally:
        api.destroy()


if __name__ == "__main__":
    main()
