#!/usr/bin/env python3
"""
OpenDSS API bridge for DaceDSX.
Mirrors the public interface of PyPSAAPI so OpenDSSWrapper.py can call it
the same way PyPSAWrapper.py calls PyPSAAPI.
"""

from __future__ import print_function
import os
import pandas as pd
from opendssdirect import dss


class OpenDSSAPI(object):

    def __init__(self, circuit_path, timesync, consumer, producer, scenarioID,
                 other_instance_topics, instanceID, step_length=3600,
                 simulationEnd=24, w="", wcb=None, to_observe=None, parameters=[]):
        if to_observe is None:
            to_observe = []
        self.circuit_path = circuit_path
        self.timeSync = timesync
        self.consumer = consumer
        self.producer = producer
        self.scenarioID = scenarioID
        self.instanceID = instanceID
        self.other_instance_topics = other_instance_topics
        self.step_length = step_length
        self.simulation_time = simulationEnd * step_length
        self.to_observe = to_observe
        self.parameters = parameters
        self.buses_at_cut = []
        self.results = []
        self._converged = False

    def init(self, responsibility):
        dss("Clear")
        dss(f'Compile "{self.circuit_path}"')
        dss("Set mode=snapshot")
        print(f"[OpenDSSAPI] Compiled circuit: {self.circuit_path}", flush=True)

        if responsibility and responsibility != ["*"]:
            self.buses_at_cut = list(responsibility)
        else:
            cb = self.parameters.get("copy_buses", "") if self.parameters else ""
            self.buses_at_cut = [b.strip() for b in cb.split(",") if b.strip()] \
                if isinstance(cb, str) else list(cb)
        if not self.buses_at_cut:
            self.buses_at_cut = list(dss.Circuit.AllBusNames())
        print(f"[OpenDSSAPI] buses_at_cut={self.buses_at_cut}", flush=True)

        topics = [self.get_topic(b) for b in self.buses_at_cut]
        try:
            self.producer.create_topics(topics)
        except Exception as e:
            print(f"[OpenDSSAPI] create_topics warning: {e}", flush=True)

    def prepareStep(self, step):
        base_kw = float(self.parameters.get("base_kw", 1800)) \
            if self.parameters else 1800
        base_kvar = float(self.parameters.get("base_kvar", 600)) \
            if self.parameters else 600
        factor = 0.5 + 0.5 * abs((step % 24) / 24)
        try:
            dss(f"Edit Load.Load1 kw={base_kw*factor:.2f} kvar={base_kvar*factor:.2f}")
        except Exception as e:
            print(f"[OpenDSSAPI] prepareStep: {e}", flush=True)

    def step(self, step):
        dss.Solution.Solve()
        self._converged = bool(dss.Solution.Converged())

    def processStep(self, step):
        if not self._converged:
            print(f"[OpenDSSAPI] step {step} did NOT converge", flush=True)
            return
        for bus in self.buses_at_cut:
            value = self.get_bus(bus)
            try:
                self.producer.produce(self.get_topic(bus), value)
            except Exception as e:
                print(f"[OpenDSSAPI] produce {bus}: {e}", flush=True)
        self.results.append({"step": step,
                             "buses": {b: self.get_bus(b) for b in self.buses_at_cut}})

    def postStep(self, step, timeInMS=0):
        return

    def get_bus(self, bus_name):
        try:
            dss.Circuit.SetActiveBus(str(bus_name))
            v = dss.Bus.VMagAngle()
            return {
                "name":     str(bus_name),
                "v_mag_pu": str(v[0]) if v and len(v) > 0 else "0",
                "v_ang":    str(v[1]) if v and len(v) > 1 else "0",
                "p": "0", "q": "0", "control": "PQ",
            }
        except Exception as e:
            print(f"[OpenDSSAPI] get_bus {bus_name}: {e}", flush=True)
            return {"name": str(bus_name), "v_mag_pu": "0", "v_ang": "0",
                    "p": "0", "q": "0", "control": "PQ"}

    def get_topic(self, s):
        return ("provision.simulation." + self.scenarioID + ".energy." +
                self.instanceID + "." + s).replace(" ", "_")

    def get_ghost_topics(self, g):
        return [(t + "." + g).replace(" ", "_") for t in self.other_instance_topics]

    def write_results(self):
        try:
            rows = []
            for e in self.results:
                for bn, v in e["buses"].items():
                    rows.append({"step": e["step"], "bus": bn,
                                 "v_mag_pu": v["v_mag_pu"], "v_ang": v["v_ang"]})
            df = pd.DataFrame(rows)
            outdir = os.path.join(os.path.dirname(__file__), "..",
                                  "_data", "results")
            os.makedirs(outdir, exist_ok=True)
            out = os.path.join(outdir,
                f"opendss_results_{self.scenarioID}_{self.instanceID}.csv")
            df.to_csv(out, index=False)
            print(f"[OpenDSSAPI] Results: {out}", flush=True)
        except Exception as e:
            print(f"[OpenDSSAPI] write_results: {e}", flush=True)

    def destroy(self):
        print("[OpenDSSAPI] destroy()", flush=True)
