"""Validate the real Kafka run and compare it with native Windows OpenDSS."""
import csv
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
summary = json.loads((HERE / "summary.json").read_text())
assert summary["all_converged"] and summary["failure_reporting_verified"]
with (HERE / "results.csv").open() as stream:
    rows = list(csv.DictReader(stream))
with (ROOT / "_data/results/opendss_four_bus_local/results.csv").open() as stream:
    local = {(r["time_ms"], r["name"]): r for r in csv.DictReader(stream)}
assert len(rows) == 40
assert {int(r["time_ms"]) for r in rows} == set(range(0, 10000, 1000))
assert len({(r["time_ms"], r["name"]) for r in rows}) == 40
maximum_difference = 0.0
for row in rows:
    reference = local[(row["time_ms"], row["name"])]
    for field in ("p", "q", "v_mag_pu", "v_ang"):
        value = float(row[field])
        assert math.isfinite(value), (row, field)
        maximum_difference = max(maximum_difference, abs(value - float(reference[field])))
assert maximum_difference < 1e-8, maximum_difference
verification = {"bus_records": len(rows), "snapshots": 10,
                "all_numeric_values_finite": True,
                "windows_vs_kafka_max_absolute_difference": maximum_difference,
                "comparison_tolerance": 1e-8,
                "failure_reporting_verified": True}
(HERE / "verification.json").write_text(json.dumps(verification, indent=2) + "\n")
print(json.dumps(verification, indent=2))
