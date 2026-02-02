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

import pandapower as pp


class pandapowerAPI(object):
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
        self.network = pp.create_empty_network()
        self.step_length = step_length  # Timestep in sec
        self.simulation_time = simulationEnd * step_length  # simulation time in sec
        self.network_path = network_path
        self.parameters = parameters

        self.timeSync = timesync
        self.to_observe = to_observe
        self.buses_at_cut = []

    def init(self, responsibility):
        if self.network_path.endswith(".json"):
            self.network = pp.from_json(self.network_path)
        elif self.network_path.endswith(".xlsx"):
            self.network = pp.from_excel(self.network_path)
        elif self.network_path.endswith(".p"):
            self.network=pp.from_pickle(self.network_path)
        else:
            print("could not load network from resource!")
            # self.network.import_from_csv_folder(self.network_path)
        if responsibility and responsibility != ["*"]:
            self.buses_at_cut = self.get_cuts(responsibility)
            self.extract_network(responsibility)
            self.buses_at_cut = responsibility
        else:
            print("PARAMETERS", self.parameters)
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
        self.buses = {}
        for bus in self.network.bus.iterrows():
            self.buses[self.network.bus.name[bus[0]]]=bus[0]


    def prepareStep(self, step):
        pass

    def step(self, step):
        # self.network.pf(snapshots=self.network.snapshots[step])
        pp.runpp_3ph(self.network)

    ##################
    ### process the last simulation step. mainly check if vehicles are going to be sent out
    def get_ghost_topics(self, ghost):
        topics = []
        for topic in self.other_instance_topics:
            topics.append((topic+"."+ghost).replace(' ', '_'))
        return topics
    def set_values_pp(self, ex, bus, v_mag, v_ang, p, q):
        if ex:
            self.network.ext_grid.vm_pu[0] = v_mag
            self.network.ext_grid.va_degree[0] = v_ang
        else:
            for elem in pp.toolbox.get_connected_elements(self.network, "sgen", self.buses[bus]):
                if self.network.sgen.name[elem] == bus + "_gen":
                    self.network.asymmetric_sgen.p_mw[elem] = p
                    self.network.asymmetric_sgen.q_mvar[elem] = q

# TODO
    def processStep(self, step):
        self.observe(step)
        for bus in self.buses_at_cut:
            topic = self.get_topic(bus)
            value = self.get_bus(bus, step)
            msg = self.producer.produce(topic, value)

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
                    voltage_ist_ghost = self.network.res_bus_3ph.vm_a_pu[self.buses[copy_bus]]
                    msg_overlap = None
                    overlap_p = 0
                    overlap_q = 0
                    overlap_v_mag_pu = 0
                    for msg in msgs:
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
                        v_diff = voltage_ist_ghost - overlap_v_mag_pu
                        p = 0
                        q = 0
                        ex=False
                        for elem in pp.toolbox.get_connected_elements(self.network, "ext_grid", self.buses[copy_bus]):
                            p = self.network.res_ext_grid_3ph.p_a_mw + self.network.res_ext_grid_3ph.p_b_mw + self.network.res_ext_grid_3ph.p_c_mw
                            q = self.network.res_ext_grid_3ph.q_a_mvar + self.network.res_ext_grid_3ph.q_b_mvar + self.network.res_ext_grid_3ph.q_c_mvar
                            ex=True
                        for elem in pp.toolbox.get_connected_elements(self.network, "sgen", self.buses[copy_bus]):
                            if self.network.sgen.name[elem] == copy_bus + "_gen":
                                p = self.network.res_ext_grid_3ph.p_a_mw[elem] + self.network.res_ext_grid_3ph.p_b_mw[elem] + self.network.res_ext_grid_3ph.p_c_mw[elem]
                                q = self.network.res_ext_grid_3ph.q_a_mvar[elem] + self.network.res_ext_grid_3ph.q_b_mvar[elem] + self.network.res_ext_grid_3ph.q_c_mvar[elem]
                        p_diff = abs(float(p)) - abs(overlap_p)
                        q_diff = abs(float(q) - abs(overlap_q))
                        print("diffs", v_diff, p_diff, q_diff)

                        if abs(v_diff) > 1e-8 or abs(p_diff) > 1e-8 or abs(q_diff) > 1e-8:
                            self.set_values_pp(ex, self.buses[copy_bus], overlap_v_mag_pu, msg.value()['v_ang'], overlap_p, overlap_q)
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

#TODO
    def get_bus(self, bus_name, snapshot):
        power_system = {}
        try:
            power_system["name"] = str(bus_name)
            p = 0
            q = 0
            for elem in pp.toolbox.get_connected_elements(self.network, "ext_grid", self.buses[bus_name]):
                # if self.network.ext_grid.name[elem] == bus_name + "_gen":
                p = float(self.network.res_ext_grid_3ph.p_a_mw[0]+ self.network.res_ext_grid_3ph.p_b_mw[0]+self.network.res_ext_grid_3ph.p_c_mw[0])
                q = float(self.network.res_ext_grid_3ph.q_a_mvar[0] + self.network.res_ext_grid_3ph.q_b_mvar[0] + self.network.res_ext_grid_3ph.q_c_mvar[0])
            for elem in pp.toolbox.get_connected_elements(self.network, "sgen", self.buses[bus_name]):
                if self.network.sgen.name[elem] == self.buses[bus_name] + "_gen":
                    p = float(self.network.res_ext_grid_3ph.p_a_mw[0]+ self.network.res_ext_grid_3ph.p_b_mw[0]+self.network.res_ext_grid_3ph.p_c_mw[0])
                    q = float(self.network.res_ext_grid_3ph.q_a_mvar[0] + self.network.res_ext_grid_3ph.q_b_mvar[0] + self.network.res_ext_grid_3ph.q_c_mvar[0])
            power_system["p"] = str(p)
            power_system["q"] = str(q)
            power_system["v_mag_pu"] = str(self.network.res_bus_3ph.vm_a_pu[self.buses[bus_name]])
            power_system["v_ang"] = str(self.network.res_bus_3ph.va_a_degree[self.buses[bus_name]])
            power_system["control"] = str("Slack")
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
        indexes = []
        for bus in self.network.bus.iterrows():
            if self.network.bus.name[bus[0]] in responsibility:
                indexes.append(bus[0])
        self.network = pp.toolbox.select_subnet(self.network, indexes)

    def get_cuts(self, responsibility):
        indexes = []
        for bus in self.network.bus.iterrows():
            if self.network.bus.name[bus[0]] in responsibility:
                indexes.append(bus[0])
        for bus in indexes:
            for elem in pp.toolbox.get_connected_buses(self.network, bus):
                if elem not in indexes:
                    self.buses_at_cut.append(self.network.bus.name[bus])

    def create_interface(self):
        for bus in self.network.bus.iterrows():
            if self.network.bus.name[bus[0]] in self.buses_at_cut:
                if not pp.toolbox.get_connected_elements(self.network, "ext_grid", bus[0]):
                    pp.create_sgen(self.network, self.network.bus.loc[bus[0]], p_mw=0)

    def destroy(self):
        """Destroys all actors"""
        print("todo: destroy()")

    def write_results(self):
        bus_rows = []
        line_rows = []

        for values in self.network.bus.iterrows():
            bus_id = values[0]
            v_mag = self.network.res_bus_3ph.vm_a_pu[values[0]]
            v_ang = self.network.res_bus_3ph.va_a_degree[values[0]]
            bus_rows.append({
                "bus": bus_id,
                "v_mag": v_mag,
                "v_ang": v_ang
            })

        for values in self.network.line.iterrows():
            p0 = self.network.res_line_3ph.p_a_from_mw[values[0]]
            q0 = self.network.res_line_3ph.q_a_from_mvar[values[0]]
            line_id = values[0]
            line_rows.append({
                "line": line_id,
                "p0": p0,
                "q1": q0
            })

            df_bus = pd.DataFrame(bus_rows)
            df_line = pd.DataFrame(line_rows)

            with pd.ExcelWriter(f"powerflow_results_{self.scenarioID}_{self.instanceID}.xlsx",
                                engine="openpyxl") as writer:
                df_bus.to_excel(writer, sheet_name="Bus", index=False)
                df_line.to_excel(writer, sheet_name="Line", index=False)
