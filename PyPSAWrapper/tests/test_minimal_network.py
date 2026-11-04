"""Regression checks for uncoupled initialization and multi-snapshot export."""

import json
from pathlib import Path
import sys
import tempfile
import unittest

import pandas as pd
import pypsa

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "PyPSAWrapper"))
from PyPSAApi import PyPSAAPI


def make_api(parameters=None):
    return PyPSAAPI(str(ROOT / "_data/resources/minimal_network.hdf5"),
                    None, None, None, "minimal_network_", [], "PyPSAWrapper0",
                    step_length=0.001, simulationEnd=2, parameters=parameters)


class MinimalNetworkTests(unittest.TestCase):
    def test_missing_or_empty_copy_buses_needs_no_communication(self):
        for parameters in (None, {}, {"copy_buses": ""}):
            with self.subTest(parameters=parameters):
                api = make_api(parameters)
                api.init([])
                self.assertEqual(api.buses_at_cut, [])
                self.assertEqual(list(api.snapshots), [1, 2])
                api.postStep(0)

    def test_scenario_converges_and_exports_both_snapshots(self):
        scenario = json.loads((ROOT / "_data/scenarios/minimal_network.json").read_text())
        block = scenario["buildingBlocks"][0]
        api = make_api(block["parameters"])
        api.init(block["responsibilities"])
        for step in range(2):
            result = api.step(step)
            self.assertTrue(result["converged"].to_numpy().all())
        network = api.network
        losses = (network.lines_t.p0 + network.lines_t.p1).sum(axis=1)
        residual = network.generators_t.p.sum(axis=1) - network.loads_t.p.sum(axis=1) - losses
        self.assertLess(residual.abs().max(), 1e-8)
        with tempfile.TemporaryDirectory() as directory:
            path = api.write_results(Path(directory) / "nested/results.xlsx")
            buses = pd.read_excel(path, sheet_name="Bus")
            lines = pd.read_excel(path, sheet_name="Line")
            self.assertEqual(len(buses), 4)
            self.assertEqual(len(lines), 2)
            self.assertEqual(set(buses["snapshot"]), {1, 2})
            self.assertEqual(set(lines["snapshot"]), {1, 2})
            self.assertAlmostEqual(lines["q0"].iloc[0], network.lines_t.q0.iloc[0, 0])
            self.assertAlmostEqual(lines["q1"].iloc[0], network.lines_t.q1.iloc[0, 0])

    def test_export_without_lines_still_writes_bus_results(self):
        api = make_api()
        api.network = pypsa.Network()
        api.network.add("Bus", "slack", v_nom=20)
        api.network.add("Generator", "gen", bus="slack", control="Slack")
        api.step(0)
        with tempfile.TemporaryDirectory() as directory:
            path = api.write_results(Path(directory) / "results.xlsx")
            self.assertEqual(len(pd.read_excel(path, sheet_name="Bus")), 1)
            self.assertTrue(pd.read_excel(path, sheet_name="Line").empty)


if __name__ == "__main__":
    unittest.main()
