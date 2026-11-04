#!/usr/bin/env python3

import json
import os
from pathlib import Path

# <repo>/_data/results, independent of the directory a wrapper is started from
RESULTS_ROOT = Path(__file__).resolve().parents[3] / "_data" / "results"


def result_dir(scenarioID, instanceID=None):
    """Directory for the results of one run (_data/results/<scenarioID>) or of one of its
    instances (_data/results/<scenarioID>/<instanceID>). Created if missing."""
    path = RESULTS_ROOT / _safe(scenarioID)
    if instanceID is not None:
        path = path / _safe(instanceID)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_scenario(scenarioID, scenario):
    """Stores the scenario a run was started with as _data/results/<scenarioID>/scenario.json.
    Every wrapper of the run calls this with the same scenario, so the file is replaced atomically."""
    target = result_dir(scenarioID) / "scenario.json"
    tmp = target.with_name(f"scenario.json.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(scenario, indent=2, default=str))
    os.replace(tmp, target)
    return target


def _safe(name):
    return str(name).replace(os.sep, "_")
