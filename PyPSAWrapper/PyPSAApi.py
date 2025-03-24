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


class PyPSAAPI(object):
    """ Class representing the surrounding environment """

    def __init__(self, network_path, timesync, consumer, producer, scenarioID, other_instance_topics, instanceID,
                 step_length=3600, simulationEnd=24, w="", wcb=None, to_observe=None):
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
            self.extract_network(responsibility)
        snapshot = list(range(1,int(self.simulation_time / self.step_length)+1))
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
        self.network.pf(snapshots=self.network.snapshots[step])

    ##################
    ### process the last simulation step. mainly check if vehicles are going to be sent out

    def processStep(self, step):
        self.observe(self.snapshots[step])
        for bus in self.buses_at_cut:
            topic = self.get_topic(bus)
            value = self.get_bus(bus, self.snapshots[step])
            msg = self.producer.produce(topic, value)
        print(self.network.lines_t.p0)

    def postStep(self, step, timeInMS=0):
        pass

    def get_bus(self, bus_name, snapshot):
        power_system = {}
        try:
            p_dict = {}
            q_dict = {}
            for line in self.network.lines.iterrows():
                if line[1].get("bus0") == bus_name:  # and line[1].get("bus1") in self.ghosts:
                    # print("Here2", self.network.lines_t.p0)
                    p_dict[str(line[0])] = str(self.network.lines_t.p0[line[0]][snapshot])
                    q_dict[str(line[0])] = str(self.network.lines_t.q0[line[0]][snapshot])

                if line[1].get("bus1") == bus_name:  # and line[1].get("bus0") in self.ghosts:
                    p_dict[str(line[0])] = str(-self.network.lines_t.p0[line[0]][snapshot])
                    q_dict[str(line[0])] = str(-self.network.lines_t.q0[line[0]][snapshot])
            print("p_dict before sending:", p_dict, bus_name, flush=True)
            for transformer in self.network.transformers.iterrows():
                # print("Here2", transformer[0])
                if transformer[1].get("bus0") == bus_name:  # and line[1].get("bus1") in self.ghosts:
                    p_dict[str(transformer[0])] = str(self.network.transformers_t.p0[transformer[0]][snapshot])
                    q_dict[str(transformer[0])] = str(self.network.transformers_t.q0[transformer[0]][snapshot])

                if transformer[1].get("bus1") == bus_name:  # and line[1].get("bus0") in self.ghosts:
                    p_dict[str(transformer[0])] = str(-self.network.transformers_t.p0[transformer[0]][snapshot])
                    q_dict[str(transformer[0])] = str(-self.network.transformers_t.q0[transformer[0]][snapshot])
            power_system["name"] = str(bus_name)
            power_system["p"] = str(p_dict)
            power_system["q"] = str(q_dict)
            power_system["v_mag_pu"] = str(self.network.buses_t.v_mag_pu[bus_name][snapshot])
            power_system["v_ang"] = str(self.network.buses_t.v_ang[bus_name][snapshot]) + '#' + str(
                self.network.buses.v_nom[bus_name])
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

    def extract_network(self, responsibility):
        busses_to_remove = []
        for bus in self.network.buses.iterrows():
            if bus[0] not in responsibility:
                busses_to_remove.append(bus[0])
        self.network.mremove("Bus", busses_to_remove)

        links_to_remove = []
        for link in self.network.links.iterrows():
            if link[1].get("bus0") not in responsibility or link[1].get("bus1") not in responsibility:
                links_to_remove.append(link[0])
        self.network.mremove("Link", links_to_remove)

        lines_to_remove = []
        for line in self.network.lines.iterrows():
            if line[1].get("bus0") not in responsibility or line[1].get("bus1") not in responsibility:
                lines_to_remove.append(line[0])
        self.network.mremove("Line", lines_to_remove)

        generators_to_remove = []
        for generator in self.network.generators.iterrows():
            if generator[1].get("bus") not in responsibility:
                generators_to_remove.append(generator[0])
        self.network.mremove("Generator", generators_to_remove)

        storage_units_to_remove = []
        for storage_unit in self.network.storage_units.iterrows():
            if storage_unit[1].get("bus") not in responsibility:
                storage_units_to_remove.append(storage_unit[0])
        self.network.mremove("StorageUnit", storage_units_to_remove)

        shunt_impedances_to_remove = []
        for shunt_impedance in self.network.shunt_impedances.iterrows():
            if shunt_impedance[1].get("bus") not in responsibility:
                shunt_impedances_to_remove.append(shunt_impedance[0])
        self.network.mremove("ShuntImpedance", shunt_impedances_to_remove)

        transformers_to_remove = []
        for transformer in self.network.transformers.iterrows():
            if transformer[1].get("bus0") not in responsibility or transformer[1].get("bus1") not in responsibility:
                transformers_to_remove.append(transformer[0])
        self.network.mremove("Transformer", transformers_to_remove)

        stores_to_remove = []
        for store in self.network.stores.iterrows():
            if store[1].get("bus") not in responsibility:
                stores_to_remove.append(store[0])
        self.network.mremove("Store", stores_to_remove)

        loads_to_remove = []
        for load in self.network.loads.iterrows():
            if load[1].get("bus") not in responsibility:
                loads_to_remove.append(load[0])
        self.network.mremove("Load", loads_to_remove)

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
