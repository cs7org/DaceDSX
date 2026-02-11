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

import pandas as pd

pd.options.mode.chained_assignment = None

import pypsa
import numpy as np


class PyPSAAPI(object):
    """ Class representing the surrounding environment """

    def __init__(self, network_path, timesync, consumer, producer, scenarioID, other_instance_topics, instanceID,
                 step_length=3600, simulationEnd=24, w="", wcb=None, to_observe=None, parameters=[]):
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
        self.parameters = parameters

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
            self.buses_at_cut = self.parameters["copy_buses"].split(", ")
            self.create_interface()
        topics = []
        topics_to_create = []
        for ghost in self.buses_at_cut:
            topics_to_create.append(self.get_topic(ghost))
            for topic in self.get_ghost_topics(ghost):
                if self.producer.topic_exists(topic):
                    topics.append(topic)
        if topics_to_create:
            self.producer.create_topics(topics_to_create)
        if topics:
            self.consumer.subscribe(topics)
        snapshot = list(range(1, int(self.simulation_time / self.step_length) + 1))
        self.snapshots = self.network.snapshots
        if len(self.network.snapshots) < len(snapshot):
            self.network.set_snapshots(snapshot)

        else:
            if 'now' not in str(self.snapshots):
                snap = pd.date_range(self.snapshots[0], self.snapshots[len(snapshot) - 1], periods=len(snapshot))
                self.network.set_snapshots(snap)
        self.snapshots = self.network.snapshots

    def prepareStep(self, step):
        pass

    def step(self, step):
        self.network.pf(snapshots=self.network.snapshots[step], x_tol=1e-11)

    ##################
    ### process the last simulation step. mainly check if vehicles are going to be sent out

    def processStep(self, step):
        self.observe(self.snapshots[step])
        print("buses_at_cut", self.buses_at_cut)
        for bus in self.buses_at_cut:
            topic = self.get_topic(bus)
            value = self.get_bus(bus, self.snapshots[step])
            msg = self.producer.produce(topic, value)
            print("msg", msg)

    def set_values_pypsa(self, ghost_bus, ghost_gen, v_mag, v_ang, p, q):
        if self.network.generators.control[ghost_gen] == "Slack":
            self.network.buses.v_mag_pu_set[ghost_bus] = v_mag
            # self.network.buses.v_ang_set[ghost_bus] = v_ang
            self.network.generators.p_set[ghost_gen] = -p
        else:
            self.network.generators.p_set[ghost_gen] = -p
            self.network.generators.q_set[ghost_gen] = -q
            self.network.generators.control[ghost_gen] = "PQ"

    def postStep(self, step, timeInMS=0):
        print("In poststep", flush=True)
        msg = self.consumer.poll(5)
        do_step = True
        msgs = []
        change = False
        while (do_step):
            topics = []
            print("next_step", flush=True)
            do_step = False
            while msg:
                msgs.append(msg)
                msg = self.consumer.poll(1)
            if msgs:
                change = False
                for copy_bus in self.buses_at_cut:
                    voltage_ist_ghost = self.network.buses_t.v_mag_pu[copy_bus][step]
                    msg_overlap = None
                    overlap_p = 0
                    overlap_q = 0
                    overlap_v_mag_pu = 0
                    for msg in msgs:
                        print("msg_overlap.value()['v_ang']", msg.value()['v_ang'], "name", msg.value()['name'],
                              "topic", msg.topic(), topics)
                        if msg.value()['name'] == copy_bus:
                            topic = msg.topic()
                            if topic not in topics:
                                topics.append(topic)
                                msg_overlap = msg
                                overlap_p = overlap_p + float(msg_overlap.value()['p'])
                                overlap_q = overlap_q + float(msg_overlap.value()['q'])
                                if msg_overlap.value()['control'] == "PQ" or msg_overlap.value()['control'] == "PV":
                                    overlap_v_mag_pu = float(msg_overlap.value()['v_mag_pu'])

                    if msg_overlap:
                        # overlap_v_ang = float(msg_overlap.value()['v_ang'])
                        # overlap_v_mag_pu = float(msg_overlap.value()['v_mag_pu'])
                        if overlap_v_mag_pu == 0:
                            overlap_v_mag_pu = float(msg_overlap.value()['v_mag_pu'])
                        print("voltage_ist_ghost", voltage_ist_ghost, "overlap_v_mag_pu", overlap_v_mag_pu, "p",
                              float(self.network.generators_t.p[copy_bus + "_gen"][step]), overlap_p, "q",
                              float(self.network.generators_t.q[copy_bus + "_gen"][step]), overlap_q)
                        v_diff = voltage_ist_ghost - overlap_v_mag_pu
                        p_diff = abs(float(self.network.generators_t.p[copy_bus + "_gen"][step])) - abs(overlap_p)
                        q_diff = abs(float(self.network.generators_t.q[copy_bus + "_gen"][step])) - abs(overlap_q)
                        print("diffs", v_diff, p_diff, q_diff)
                        print(self.network.buses.control, self.network.generators)
                        contrl = self.network.generators.control[copy_bus + "_gen"]
                        print("contrl", contrl, flush=True)
                        if abs(v_diff) > 1e-8 or abs(p_diff) > 1e-8 or abs(q_diff) > 1e-8:
                            self.set_values_pypsa(copy_bus, copy_bus + "_gen", overlap_v_mag_pu, msg.value()['v_ang'],
                                                  overlap_p, overlap_q)
                            change = True
                        else:
                            do_step = False
                # print("self.network.generators.p_set",self.network.generators.p_set, flush=True)
                print("do_step", do_step, change)
            send_msgs = False
            if do_step or change:
                self.timeSync.timeAdvance(0)
                self.step(step)
                print("DOING STEP", flush=True)
                self.processStep(step)
                # self.postStep(step)
                do_step = True
                send_msgs = True
            msgs = []
            msg = self.consumer.poll(5)
            if msg:
                msgs.append(msg)
                do_step = True
                if not send_msgs:
                    self.timeSync.timeAdvance(0)
                    self.step(step)
                    print("send_msgs", flush=True)
                    self.processStep(step)
                print("DOING STEP", flush=True)

            # msg = self.consumer.poll(5)
            # print('the new msg', msg, flush=True)

        if (timeInMS > 100000 and timeInMS % 1000 == 0):
            print(f"Post-processing for step {timeInMS}")

        return

    def get_bus(self, bus_name, snapshot):
        power_system = {}
        try:
            power_system["name"] = str(bus_name)
            power_system["p"] = str(self.network.generators_t.p[bus_name + "_gen"][snapshot])
            power_system["q"] = str(self.network.generators_t.q[bus_name + "_gen"][snapshot])
            power_system["v_mag_pu"] = str(self.network.buses_t.v_mag_pu[bus_name][snapshot])
            power_system["v_ang"] = str(self.network.buses_t.v_ang[bus_name][snapshot])
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
            msg = self.producer.produce(topic, value)

    def get_topic(self, string):
        return ("provision.simulation." + self.scenarioID + ".energy." + self.instanceID + '.' + string).replace(" ",
                                                                                                                 "_")

    def get_ghost_topics(self, ghost):
        topics = []
        for topic in self.other_instance_topics:
            topics.append((topic + "." + ghost).replace(' ', '_'))
        return topics

    def create_interface(self):
        for bus in self.network.buses.iterrows():
            if bus[0] not in self.buses_at_cut:
                pass
            else:
                if self.network.buses.control[bus[0]] != "Slack":
                    self.network.add("Generator", bus[0] + "_gen", bus=bus[0], control="PQ", p_set=0)
                    self.network.buses.control[bus[0]] = "PQ"
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
                    self.network.buses.control[bus[0]] = "PQ"
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

    def write_results(self):
        bus_rows = []
        line_rows = []

        for values in self.network.buses.iterrows():
            bus_id = values[0]
            v_mag = self.network.buses_t.v_mag_pu[values[0]]['now']
            v_ang = self.network.buses_t.v_ang[values[0]]['now']
            bus_rows.append({
                "bus": bus_id,
                "v_mag": v_mag,
                "v_ang": v_ang
            })

        for values in self.network.lines.iterrows():
            p0 = self.network.lines_t.p0[values[0]]['now']
            q0 = self.network.lines_t.q0[values[0]]['now']
            line_id = values[0]
            line_rows.append({
                "line": line_id,
                "p0": p0,
                "q1": q0
            })

            df_bus = pd.DataFrame(bus_rows)
            df_line = pd.DataFrame(line_rows)

            with pd.ExcelWriter(f"../_data/results/powerflow_results_{self.scenarioID}_{self.instanceID}.xlsx",
                                engine="openpyxl") as writer:
                df_bus.to_excel(writer, sheet_name="Bus", index=False)
                df_line.to_excel(writer, sheet_name="Line", index=False)
