#!/usr/bin/env python3
#
# Copyright (c) 2025 Informatik 7 Friedrich-Alexander Universität Erlangen-Nürnberg,
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#


from __future__ import print_function

import os
import sys
from pathlib import Path

import pandas as pd

pd.options.mode.chained_assignment = None

import pypsa
import numpy as np

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../PythonBaseWrapper/src/communication')
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../PythonBaseWrapper/src/logic')
from MessageBuffer import collectPeerMsgs
from ResultDir import result_dir

# boundary values at the copy buses count as unchanged below this difference (pu, MW, MVAr)
COUPLING_TOL = 1e-6
COUPLING_MAX_ITERATIONS = 50


class PyPSAAPI(object):
    """ Class representing the surrounding environment """

    def __init__(self, network_path, timesync, consumer, producer, scenarioID, other_instance_topics, instanceID,
                 step_length=3600, simulationEnd=24, w="", wcb=None, to_observe=None, parameters=None, peers=None):
        # print("\n\n_____init_____\n\n", flush=True)
        if to_observe is None:
            to_observe = []
        self.wrapper_cb = wcb
        self.consumer = consumer
        self.producer = producer
        self.scenarioID = scenarioID
        self.recOn = 0
        self.other_instance_topics = other_instance_topics
        self.instanceID = instanceID
        self.network = pypsa.Network()
        self.step_length = step_length  # Timestep in sec
        self.simulation_time = simulationEnd * step_length  # simulation time in sec
        self.network_path = network_path
        self.buses = self.network.buses

        self.generators = self.network.generators

        self.loads = self.network.loads

        self.lines = self.network.lines

        self.transformers = self.network.transformers
        self.snapshots = self.network.snapshots
        self.timeSync = timesync
        self.to_observe = to_observe
        self.buses_at_cut = []
        self.parameters = parameters or {}
        # other power flow instances and the buses they couple at, from the scenario
        self.peers = peers or {}
        # topics of the peers at the copy buses, set in init
        self.ghost_topics = []
        # power flow results per step, written by write_results
        self.bus_rows = []
        self.line_rows = []

    def init(self, responsibility):
        self.network = pypsa.Network()
        if self.network_path.endswith(".hdf5"):
            self.network.import_from_hdf5(self.network_path)
        elif self.network_path.endswith(".cdf") or self.network_path.endswith(".nc"):
            self.network.import_from_netcdf(self.network_path)
        else:
            print("could not load network from resource!")
            self.network.import_from_csv_folder(self.network_path)
        if responsibility and responsibility != ["*"]:
            self.buses_at_cut = self.get_cuts(responsibility)
            self.extract_network(responsibility, self.buses_at_cut)
        else:
            self.buses_at_cut = [bus.strip() for bus in self.parameters.get("copy_buses", "").split(",")
                                 if bus.strip()]
            if self.buses_at_cut:
                self.create_interface()
        topics_to_create = [self.get_topic(ghost) for ghost in self.buses_at_cut]
        # the peers' topics are known from the scenario, creating them here as well makes the
        # subscription independent of which instance starts first
        self.ghost_topics = [self.get_peer_topic(peer, bus) for bus in self.buses_at_cut
                             for peer, buses in self.peers.items() if bus in buses]
        topics_to_create += self.ghost_topics
        if topics_to_create:
            self.producer.create_topics(topics_to_create)
        if self.ghost_topics:
            self.consumer.subscribe(self.ghost_topics)
        snapshot = list(range(1, int(self.simulation_time / self.step_length) + 1))
        self.snapshots = self.network.snapshots
        if len(self.network.snapshots) < len(snapshot):
            self.network.set_snapshots(snapshot)

        else:
            self.network.set_snapshots(self.snapshots[:len(snapshot)])
        self.snapshots = self.network.snapshots

    def prepareStep(self, step):
        pass

    def step(self, step):
        return self.network.pf(snapshots=self.network.snapshots[step], x_tol=1e-11)

    ##################
    ### process the last simulation step. mainly check if vehicles are going to be sent out

    def processStep(self, step):
        self.observe(self.snapshots[step])
        print("buses_at_cut", self.buses_at_cut)
        for bus in self.buses_at_cut:
            topic = self.get_topic(bus)
            value = self.get_bus(bus, self.snapshots[step])
            msg = self.producer.produce(topic, value, timestamp=self.timeSync.currentLocalTime)
            print("msg", msg)
        self.log_results(step)

    def log_results(self, step):
        """Stores the power flow result of the current time in the same form as pandapower; a repeated
        power flow in the same step (see postStep) replaces the rows of the earlier one."""
        t = self.timeSync.currentLocalTime
        snapshot = self.snapshots[step]
        n = self.network
        self.bus_rows = [r for r in self.bus_rows if r["time"] != t]
        self.line_rows = [r for r in self.line_rows if r["time"] != t]
        for bus in n.buses.index:
            self.bus_rows.append({
                "time": t,
                "bus": bus,
                "name": bus,
                "v_mag": n.buses_t.v_mag_pu.at[snapshot, bus],
                "v_ang": np.degrees(n.buses_t.v_ang.at[snapshot, bus]),
                # PyPSA counts injections positive, pandapower's res_bus consumption
                "p": -n.buses_t.p.at[snapshot, bus],
                "q": -n.buses_t.q.at[snapshot, bus]
            })
        for line in n.lines.index:
            self.line_rows.append({
                "time": t,
                "line": line,
                "name": line,
                "p0": n.lines_t.p0.at[snapshot, line],
                # reactive power at bus0, named q1 like in the pandapower results
                "q1": n.lines_t.q0.at[snapshot, line]
            })

    def postStep(self, step, timeInMS=0):
        """
        Couples the copy buses with the other power flow instances (peers): applies their latest
        boundary values, repeats the power flow and publishes the result as long as something
        changes. A side without changes stays silent, the exchange ends when nothing new arrives.
        """
        if not self.ghost_topics:
            return
        now = self.timeSync.currentLocalTime
        # every peer publishes its copy buses once per step (processStep), later only on changes
        msgs = collectPeerMsgs(self.consumer, now, timeout=30, expected=self.ghost_topics)
        for iteration in range(COUPLING_MAX_ITERATIONS):
            print("coupling iteration", iteration, "received", [m.topic() for m in msgs], flush=True)
            if not msgs:
                return
            if self.apply_peer_values(msgs):
                self.timeSync.timeAdvance(0)
                self.step(step)
                self.processStep(step)
            msgs = collectPeerMsgs(self.consumer, now, timeout=5)
        print("copy buses did not converge after", COUPLING_MAX_ITERATIONS, "iterations", flush=True)

    def apply_peer_values(self, msgs):
        """
        Sets the boundary values the peers sent for the copy buses, returns True if any changed.
        A copy bus whose interface generator is the slack takes the voltage of the peer, otherwise
        the generator takes the power: what the peers inject into their part leaves this one.
        """
        changed = False
        for copy_bus in self.buses_at_cut:
            values = [m.value() for m in msgs if m.value()['name'] == copy_bus]
            if not values:
                continue
            gen = copy_bus + "_gen"
            slack = self.network.generators.at[gen, "control"] == "Slack"
            if slack:
                # the voltage comes from a peer that computes it, not from another slack
                v = next((x for x in values if x['control'] != "Slack"), values[-1])
                new = (float(v['v_mag_pu']),)
                old = (self.network.buses.at[copy_bus, "v_mag_pu_set"],)
            else:
                new = (-sum(float(x['p']) for x in values), -sum(float(x['q']) for x in values))
                old = (self.network.generators.at[gen, "p_set"], self.network.generators.at[gen, "q_set"])
            print("copy bus", copy_bus, "slack" if slack else "pq", "old", old, "new", new, flush=True)
            if any(abs(a - b) > COUPLING_TOL for a, b in zip(old, new)):
                if slack:
                    self.network.buses.at[copy_bus, "v_mag_pu_set"] = new[0]
                else:
                    self.network.generators.loc[gen, ["p_set", "q_set"]] = new
                changed = True
        return changed

    def get_bus(self, bus_name, snapshot):
        power_system = {}
        try:
            power_system["name"] = str(bus_name)
            power_system["p"] = str(self.network.generators_t.p[bus_name + "_gen"][snapshot])
            power_system["q"] = str(self.network.generators_t.q[bus_name + "_gen"][snapshot])
            power_system["v_mag_pu"] = str(self.network.buses_t.v_mag_pu[bus_name][snapshot])
            # PyPSA works in radians, the Bus schema (and pandapower) in degrees
            power_system["v_ang"] = str(np.degrees(self.network.buses_t.v_ang[bus_name][snapshot]))
            power_system["control"] = str(self.network.buses.control[bus_name])
            # power_system["marginal_price"] = str(self.network.buses_t.marginal_price[bus_name][snapshot])
            # power_system["transformers"] = str(self.network.buses)
        except Exception as e:
            print("failed to get bus system", flush=True)
            print(e)
        return power_system

    # todo: add parameterization for multiple observers
    def observe(self, snapshot):
        for bus in self.to_observe:
            topic = self.get_topic(bus)
            value = self.get_bus(bus, snapshot)
            msg = self.producer.produce(topic, value, timestamp=self.timeSync.currentLocalTime)

    def get_topic(self, string):
        return self.get_peer_topic(self.instanceID, string)

    def get_peer_topic(self, instanceID, bus):
        """Topic on which instanceID publishes its values at a copy bus"""
        return ("provision.simulation." + self.scenarioID + ".energy.Bus." + instanceID + '.' + bus).replace(" ", "_")

    def create_interface(self):
        for bus in self.network.buses.iterrows():
            if bus[0] not in self.buses_at_cut:
                pass
            else:
                if self.network.buses.control[bus[0]] != "Slack":
                    self.network.add("Generator", bus[0] + "_gen", bus=bus[0], control="PQ", p_set=0)
                    self.network.buses.at[bus[0], "control"] = "PQ"
                else:
                    self.network.add("Generator", bus[0] + "_gen", bus=bus[0], control="Slack", p_set=0)

    def extract_network(self, responsibility, ghosts):
        # print("\n\nresponsibility after", responsibility)
        busses_to_remove = []
        for bus in self.network.buses.iterrows():
            if bus[0] not in responsibility:
                busses_to_remove.append(bus[0])
        self.network.remove("Bus", busses_to_remove)

        links_to_remove = []
        for link in self.network.links.iterrows():
            if link[1].get("bus0") not in responsibility or link[1].get("bus1") not in responsibility:
                links_to_remove.append(link[0])
        self.network.remove("Link", links_to_remove)

        lines_to_remove = []
        for line in self.network.lines.iterrows():
            if line[1].get("bus0") not in responsibility or line[1].get("bus1") not in responsibility or (
                    line[1].get("bus0") in ghosts and line[1].get("bus1") in ghosts):
                lines_to_remove.append(line[0])
        self.network.remove("Line", lines_to_remove)

        generators_to_remove = []
        for generator in self.network.generators.iterrows():
            if generator[1].get("bus") not in responsibility:
                generators_to_remove.append(generator[0])
        self.network.remove("Generator", generators_to_remove)

        storage_units_to_remove = []
        for storage_unit in self.network.storage_units.iterrows():
            if storage_unit[1].get("bus") not in responsibility:
                storage_units_to_remove.append(storage_unit[0])
        self.network.remove("StorageUnit", storage_units_to_remove)

        shunt_impedances_to_remove = []
        for shunt_impedance in self.network.shunt_impedances.iterrows():
            if shunt_impedance[1].get("bus") not in responsibility:
                shunt_impedances_to_remove.append(shunt_impedance[0])
        self.network.remove("ShuntImpedance", shunt_impedances_to_remove)

        transformers_to_remove = []
        for transformer in self.network.transformers.iterrows():
            if transformer[1].get("bus0") not in responsibility or transformer[1].get("bus1") not in responsibility:
                transformers_to_remove.append(transformer[0])
        self.network.remove("Transformer", transformers_to_remove)

        stores_to_remove = []
        for store in self.network.stores.iterrows():
            if store[1].get("bus") not in responsibility:
                stores_to_remove.append(store[0])
        self.network.remove("Store", stores_to_remove)

        loads_to_remove = []
        for load in self.network.loads.iterrows():
            if load[1].get("bus") not in responsibility:
                loads_to_remove.append(load[0])
        self.network.remove("Load", loads_to_remove)
        has_slack = False
        for bus in self.network.buses.iterrows():
            if bus[1].control == "Slack":
                has_slack = True
        for bus in self.network.buses.iterrows():
            if bus[0] not in ghosts:
                pass
            else:
                if has_slack:
                    stores_to_remove = []
                    for store in self.network.stores.iterrows():
                        if store[1].get("bus") == bus[0]:
                            stores_to_remove.append(store[0])
                    self.network.remove("Store", stores_to_remove)

                    loads_to_remove = []
                    for load in self.network.loads.iterrows():
                        if load[1].get("bus") == bus[0]:
                            loads_to_remove.append(load[0])
                    self.network.remove("Load", loads_to_remove)
                    generators_to_remove = []
                    for generator in self.network.generators.iterrows():
                        if generator[1].get("bus") == bus[0]:
                            generators_to_remove.append(generator[0])
                    self.network.remove("Generator", generators_to_remove)

                    storage_units_to_remove = []
                    for storage_unit in self.network.storage_units.iterrows():
                        if storage_unit[1].get("bus") == bus[0]:
                            storage_units_to_remove.append(storage_unit[0])
                    self.network.remove("StorageUnit", storage_units_to_remove)

                    shunt_impedances_to_remove = []
                    for shunt_impedance in self.network.shunt_impedances.iterrows():
                        if shunt_impedance[1].get("bus") == bus[0]:
                            shunt_impedances_to_remove.append(shunt_impedance[0])
                    self.network.add("Generator", bus[0] + "_gen", bus=bus[0], control="PQ", p_set=0)
                    self.network.buses.at[bus[0], "control"] = "PQ"
                else:
                    self.network.add("Generator", bus[0] + "_gen", bus=bus[0], control="Slack")

    def get_cuts(self, responsibility):
        busses_at_cut = []
        for bus in self.network.buses.iterrows():
            if bus[0] in responsibility:
                for link in self.network.links.iterrows():
                    if link[1].get("bus0") == bus[0]:
                        if link[1].get("bus1") not in responsibility and link[1].get("bus0") not in busses_at_cut:
                            busses_at_cut.append(link[1].get("bus0"))
                    if link[1].get("bus1") == bus[0]:
                        if link[1].get("bus0") not in responsibility and link[1].get("bus1") not in busses_at_cut:
                            busses_at_cut.append(link[1].get("bus1"))
                for line in self.network.lines.iterrows():
                    if line[1].get("bus0") == bus[0]:
                        if line[1].get("bus1") not in responsibility and line[1].get("bus0") not in busses_at_cut:
                            busses_at_cut.append(line[1].get("bus0"))
                    if line[1].get("bus1") == bus[0]:
                        if line[1].get("bus0") not in responsibility and line[1].get("bus1") not in busses_at_cut:
                            busses_at_cut.append(line[1].get("bus1"))
                for transformer in self.network.transformers.iterrows():
                    if transformer[1].get("bus0") == bus[0]:
                        if transformer[1].get("bus1") not in responsibility and transformer[1].get(
                                "bus0") not in busses_at_cut:
                            busses_at_cut.append(transformer[1].get("bus0"))
                    if transformer[1].get("bus1") == bus[0]:
                        if transformer[1].get("bus0") not in responsibility and transformer[1].get(
                                "bus1") not in busses_at_cut:
                            busses_at_cut.append(transformer[1].get("bus1"))
        return busses_at_cut

    def destroy(self):
        """Destroys all actors"""
        print("todo: destroy()")

    def write_results(self, output_path=None):
        if output_path is None:
            output_path = result_dir(self.scenarioID, self.instanceID) / "results.xlsx"
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            pd.DataFrame(self.bus_rows, columns=["time", "bus", "name", "v_mag", "v_ang", "p", "q"]).to_excel(
                writer, sheet_name="Bus", index=False)
            pd.DataFrame(self.line_rows, columns=["time", "line", "name", "p0", "q1"]).to_excel(
                writer, sheet_name="Line", index=False)
        return output_path
