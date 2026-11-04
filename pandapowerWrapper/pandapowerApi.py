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

from pathlib import Path
import pandas as pd
import pandapower as pp
import json
import time
from MessageBuffer import MessageBuffer
from ResultDir import result_dir

pd.options.mode.chained_assignment = None


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
        self.n_steps = simulationEnd

        self.load_profile = None
        self.sgen_profile = None
        self.bus_vm = None
        self.bus_va = None
        self.line_p = None
        self.trafo_p = None
        self.history = []

        self.timeSync = timesync
        self.to_observe = to_observe
        self.buses_at_cut = []

        # filled by the wrapper's main consumer thread, read in prepareStep
        self.translator_inbox = MessageBuffer()

    def build_network(self, data):
        net = pp.create_empty_network(
            name=data.get('name', 'network'),
            f_hz=data.get('f_hz', 50.0),
            sn_mva=data.get('sn_mva', 1)
        )
        
        for bus in data.get('bus', []):
            pp.create_bus(net, vn_kv=bus['vn_kv'], name=bus.get('name'),
                         type=bus.get('type', 'b'), in_service=bus.get('in_service', True))
        
        for eg in data.get('ext_grid', []):
            pp.create_ext_grid(net, bus=eg['bus'], vm_pu=eg.get('vm_pu', 1.0),
                              va_degree=eg.get('va_degree', 0.0), name=eg.get('name'))
        
        for tr in data.get('trafo', []):
            pp.create_transformer_from_parameters(
                net, hv_bus=tr['hv_bus'], lv_bus=tr['lv_bus'],
                sn_mva=tr['sn_mva'], vn_hv_kv=tr['vn_hv_kv'], vn_lv_kv=tr['vn_lv_kv'],
                vk_percent=tr['vk_percent'], vkr_percent=tr['vkr_percent'],
                pfe_kw=tr.get('pfe_kw', 0), i0_percent=tr.get('i0_percent', 0),
                shift_degree=tr.get('shift_degree', 0), name=tr.get('name'),
                vector_group=tr.get('vector_group'))
        
        for ln in data.get('line', []):
            pp.create_line_from_parameters(
                net, from_bus=ln['from_bus'], to_bus=ln['to_bus'],
                length_km=ln['length_km'], r_ohm_per_km=ln['r_ohm_per_km'],
                x_ohm_per_km=ln['x_ohm_per_km'], c_nf_per_km=ln.get('c_nf_per_km', 0),
                max_i_ka=ln.get('max_i_ka', 1), name=ln.get('name'))
        
        for ld in data.get('load', []):
            pp.create_load(net, bus=ld['bus'], p_mw=ld['p_mw'],
                          q_mvar=ld.get('q_mvar', 0), name=ld.get('name'))
        
        for sg in data.get('sgen', []):
            pp.create_sgen(net, bus=sg['bus'], p_mw=sg['p_mw'],
                          q_mvar=sg.get('q_mvar', 0), name=sg.get('name'))
        
        for gen in data.get('gen', []):
            pp.create_gen(net, bus=gen['bus'], p_mw=gen['p_mw'],
                         vm_pu=gen.get('vm_pu', 1.0), name=gen.get('name'))
        
        for sw in data.get('switch', []):
            pp.create_switch(net, bus=sw['bus'], element=sw['element'],
                            et=sw['et'], closed=sw.get('closed', True), name=sw.get('name'))
        
        for st in data.get('storage', []):
            pp.create_storage(net, bus=st['bus'], p_mw=st['p_mw'],
                             max_e_mwh=st['max_e_mwh'], name=st.get('name'))
        
        return net
        
    def init(self, responsibility):
        print("____init____", flush=True)
        p = Path(self.network_path)
        if not p.exists():
            raise FileNotFoundError(f"Network not found: {self.network_path}")

        ext = p.suffix.lower()
        if ext == ".json":
            with open(p, 'r') as f:
                data = json.load(f)
            if '_module' in data:
                self.network = pp.from_json(str(p))
            else:
                self.network = self.build_network(data)
        elif ext in (".xlsx", ".xls"):
            self.network = pp.from_excel(str(p))
        elif ext == ".p":
            self.network = pp.from_pickle(str(p))
        else:
            raise RuntimeError(f"Unsupported format: {ext}")
        folder = p.parent
        load_csv, load_json = folder / "load_profile.csv", folder / "load_profile.json"
        sgen_csv, sgen_json = folder / "sgen_profile.csv", folder / "sgen_profile.json"

        if load_csv.exists():
            self.load_profile = pd.read_csv(load_csv, index_col=0)
        elif load_json.exists():
            self.load_profile = pd.read_json(load_json)
            if not self.load_profile.empty:
                try:
                    self.load_profile.index = self.load_profile.index.astype(int)
                except:
                    pass
        if sgen_csv.exists():
            self.sgen_profile = pd.read_csv(sgen_csv, index_col=0)
        elif sgen_json.exists():
            self.sgen_profile = pd.read_json(sgen_json)
            if not self.sgen_profile.empty:
                try:
                    self.sgen_profile.index = self.sgen_profile.index.astype(int)
                except:
                    pass
        bus_names = [str(n) if pd.notna(n) else f"bus_{i}" for i, n in enumerate(self.network.bus.get('name', []))]
        if not bus_names:
            bus_names = [f"bus_{i}" for i in self.network.bus.index]

        line_names = [f"line_{i}" for i in self.network.line.index]
        trafo_names = [f"trafo_{i}" for i in self.network.trafo.index] if hasattr(self.network, 'trafo') else []

        # self.bus_vm = None
        # self.bus_va = None
        # self.line_p = None
        # self.trafo_p = None

        try:
            self.bus_vm = pd.DataFrame(index=range(self.n_steps), columns=bus_names, dtype=float)
            self.bus_va = pd.DataFrame(index=range(self.n_steps), columns=bus_names, dtype=float)
            self.line_p = pd.DataFrame(index=range(self.n_steps), columns=line_names, dtype=float)
            self.trafo_p = pd.DataFrame(index=range(self.n_steps), columns=trafo_names, dtype=float)
        except:
            pass
        self.three_phase = False
        try:
            if self.parameters["three_phase"] == "True" or self.parameters["three_phase"] == "true":
                self.three_phase = True
        except:
            print("Could not find three_phase parameter will use runpp to calculate")

        if responsibility and responsibility != ["*"]:
            self.buses_at_cut = self.get_cuts(responsibility)
            self.extract_network(responsibility)
            self.buses_at_cut = responsibility
        else:
            print("PARAMETERS", self.parameters)
            try:
                self.buses_at_cut = self.parameters["copy_buses"].split(", ")
                self.create_interface()
            except:
                print("No copy buses given")
        topics = []
        topics_to_create = []
        for bus in self.to_observe:
            topics_to_create.append(self.get_topic(bus))
        translator_topics = []
        for tpc in self.other_instance_topics:
            print(tpc)
            if str(tpc).endswith(".translator."):
                for bus in self.buses_at_cut:
                    translator_topics.append(tpc+str(bus).replace(" ", "_"))
                    topics_to_create.append(tpc + str(bus).replace(" ", "_"))
        for ghost in self.buses_at_cut:
            topics_to_create.append(self.get_topic(ghost))
            for topic in self.get_ghost_topics(ghost):
                if self.producer.topic_exists(topic):
                    topics.append(topic)
        print("topics_to_create",topics_to_create)
        print("topics", topics)
        if topics_to_create:
            self.producer.create_topics(topics_to_create)
        if topics:
            self.wait_for_topic(self.consumer, topics[0])
            self.consumer.subscribe(topics)
        self.buses = {}
        for bus in self.network.bus.iterrows():
            self.buses[self.network.bus.name[bus[0]]] = bus[0]

    def wait_for_topic(self, consumer, topic, timeout=10):
        start = time.time()
        while time.time() - start < timeout:
            meta = consumer.list_topics()
            print(meta.keys(), topic, topic in meta.keys(), flush=True)
            if topic in meta.keys():
                return True
            time.sleep(0.5)
        return False

    def on_translator_msg(self, inMsg):
        """Wird von processMsg im Wrapper aufgerufen"""
        self.translator_inbox.add(inMsg)

    def prepareStep(self, step):
        print("____prepareStep____", flush=True)
        if self.load_profile is not None and step in self.load_profile.index:
            for col, val in self.load_profile.loc[step].items():
                if pd.notna(val):
                    try:
                        idx = int(col) if str(col).isdigit() else None
                        if idx is not None and idx in self.network.load.index:
                            self.network.load.at[idx, 'p_mw'] = float(val)
                    except:
                        pass

        if self.sgen_profile is not None and step in self.sgen_profile.index:
            for col, val in self.sgen_profile.loc[step].items():
                if pd.notna(val):
                    try:
                        idx = int(col) if str(col).isdigit() else None
                        if idx is not None and idx in self.network.sgen.index:
                            self.network.sgen.at[idx, 'p_mw'] = float(val)
                    except:
                        pass
        # TimeSync guarantees that all messages sent before the current time have arrived,
        # messages of the current step stay buffered for the next one
        translator_msgs = self.translator_inbox.take(self.timeSync.currentLocalTime)
        print("translator_msgs", len(translator_msgs), flush=True)
        for msg in translator_msgs:
            content = msg.value()
            self.set_values_pp(False, self.buses[content["name"]], float(content["v_mag_pu"]), float(content['v_ang']),
                               float(content["p"]), float(content["q"]))

    def step(self, step):
        print("____step____", flush=True)
        if self.three_phase:
            try:
                pp.runpp_3ph(self.network)
            except Exception as e:
                print(f"Powerflow failed at step {step}: {e}")
        else:
            try:
                pp.runpp(self.network)
            except Exception as e:
                print(f"Powerflow failed at step {step}: {e}")

    ##################
    ### process the last simulation step. mainly check if vehicles are going to be sent out
    def get_ghost_topics(self, ghost):
        print("____get_ghost_topics____", flush=True)
        topics = []
        for topic in self.other_instance_topics:
            topics.append((topic + "." + ghost).replace(' ', '_'))
        return topics

    def interface_sgen_name(self, bus):
        """Name of the sgen create_interface puts at a copy bus (bus = bus index)"""
        return str(bus) + "_gen"

    def set_values_pp(self, ex, bus, v_mag, v_ang, p, q):
        # write via .at: chained assignment (net.sgen.p_mw[i] = x) silently writes to a copy
        # with pandas Copy-on-Write (default from pandas 3.0)
        print("____set_values_pp____", flush=True)
        if ex:
            print("------if EX -----------")
            for elem in pp.toolbox.get_connected_elements(self.network, "ext_grid", bus):
                self.network.ext_grid.at[elem, "vm_pu"] = v_mag
                self.network.ext_grid.at[elem, "va_degree"] = v_ang
        else:
            print("---------SGEN----------", self.buses, bus)
            name = self.interface_sgen_name(bus)
            for elem in pp.toolbox.get_connected_elements(self.network, "sgen", bus):
                if self.network.sgen.at[elem, "name"] == name:
                    self.network.sgen.at[elem, "p_mw"] = p
                    self.network.sgen.at[elem, "q_mvar"] = q
            # asymmetric_sgen has per-phase columns, split the power evenly
            for elem in pp.toolbox.get_connected_elements(self.network, "asymmetric_sgen", bus):
                if self.network.asymmetric_sgen.at[elem, "name"] == name:
                    for ph in ("a", "b", "c"):
                        self.network.asymmetric_sgen.at[elem, f"p_{ph}_mw"] = p / 3
                        self.network.asymmetric_sgen.at[elem, f"q_{ph}_mvar"] = q / 3

    def processStep(self, step):
        print("____processStep____", flush=True)
        self.observe(step)
        for bus in self.buses_at_cut:
            topic = self.get_topic(bus)
            value = self.get_bus(bus, step)
            msg = self.producer.produce(topic, value, timestamp=self.timeSync.currentLocalTime)
            self.timeSync.notifiyAboutSentMessage(topic)
        for i, idx in enumerate(self.network.bus.index):
            if self.bus_vm is not None:
                col = self.bus_vm.columns[i]
                try:
                    self.bus_vm.at[step, col] = self.network.res_bus.at[idx, 'vm_pu']
                    self.bus_va.at[step, col] = self.network.res_bus.at[idx, 'va_degree']
                except:
                    pass

        for i, idx in enumerate(self.network.line.index):
            if self.line_p is not None:
                col = self.line_p.columns[i]
                try:
                    self.line_p.at[step, col] = self.network.res_line.at[idx, 'p_from_mw']
                except:
                    pass

        if hasattr(self.network, 'res_trafo'):
            for i, idx in enumerate(self.network.trafo.index):
                if self.trafo_p is not None:
                    col = self.trafo_p.columns[i]
                    try:
                        self.trafo_p.at[step, col] = self.network.res_trafo.at[idx, 'p_hv_mw']
                    except:
                        pass

        self.history.append({'step': step})

    def postStep(self, step, timeInMS=0):
        print("___postStep___", flush=True)
        msg= None
        # msg = self.consumer.poll(10)
        if self.buses_at_cut:
            do_step = True
        else:    
            do_step = False
        msgs = []
        change = False
        while (do_step):
            topics = []
            print("next_step", flush=True)
            do_step = False
            got_message = False
            while msg:
                msgs.append(msg)
                # msg = self.consumer.poll(1)
            print("msgs", msgs, flush=True)
            if msgs:
                got_message = True
                change = False
                for copy_bus in self.buses_at_cut:
                    if self.three_phase:
                        voltage_ist_ghost = self.network.res_bus_3ph.vm_a_pu[self.buses[copy_bus]]
                    else:
                        voltage_ist_ghost = self.network.res_bus.vm_pu[self.buses[copy_bus]]
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
                        p, q, ex = self.get_interface_pq(self.buses[copy_bus])
                        print("p", p, "q", q, "voltage_ist_ghost", voltage_ist_ghost, flush=True)
                        p_diff = abs(float(p)) - abs(overlap_p)
                        q_diff = abs(float(q) - abs(overlap_q))
                        print("diffs", v_diff, p_diff, q_diff)

                        if abs(v_diff) > 1e-8 or abs(p_diff) > 1e-8 or abs(q_diff) > 1e-8:
                            self.set_values_pp(ex, self.buses[copy_bus], overlap_v_mag_pu, float(msg.value()['v_ang']),
                                               overlap_p, overlap_q)
                            print("_after_set_values________")
                            change = True
                        else:
                            do_step = False
                # print("self.network.generators.p_set",self.network.generators.p_set, flush=True)
                print("do_step", do_step, change)
            send_msgs = False
            if (do_step or change) and got_message:
                # self.timeSync.timeAdvance(0)
                self.step(step)
                print("DOING STEP", flush=True)
                self.processStep(step)
                # self.postStep(step)
                do_step = True
                send_msgs = True
            msgs = []
            # msg = self.consumer.poll(5)
            if msg:
                msgs.append(msg)
                do_step = True
                if not send_msgs:
                    # self.timeSync.timeAdvance(0)
                    self.step(step)
                    print("send_msgs", flush=True)
                    self.processStep(step)
                print("DOING STEP", flush=True)
            else:
                do_step = False

            # msg = self.consumer.poll(5)
            # print('the new msg', msg, flush=True)

        if (timeInMS > 100000 and timeInMS % 1000 == 0):
            print(f"Post-processing for step {timeInMS}")

        return

    def get_interface_pq(self, bus):
        """
        Result p [MW] / q [MVAr] of the interface element at a bus (bus = bus index):
        the ext_grid (slack) or the sgen created by create_interface.
        Returns (p, q, is_slack). Uses the element index, not row 0 of the result tables.
        """
        p, q, is_slack = 0.0, 0.0, False
        for elem in pp.toolbox.get_connected_elements(self.network, "ext_grid", bus):
            is_slack = True
            if self.three_phase:
                res = self.network.res_ext_grid_3ph
                p = float(res.at[elem, "p_a_mw"] + res.at[elem, "p_b_mw"] + res.at[elem, "p_c_mw"])
                q = float(res.at[elem, "q_a_mvar"] + res.at[elem, "q_b_mvar"] + res.at[elem, "q_c_mvar"])
            else:
                p = float(self.network.res_ext_grid.at[elem, "p_mw"])
                q = float(self.network.res_ext_grid.at[elem, "q_mvar"])

        name = self.interface_sgen_name(bus)
        for elem in pp.toolbox.get_connected_elements(self.network, "sgen", bus):
            if self.network.sgen.at[elem, "name"] == name:
                p = float(self.network.res_sgen.at[elem, "p_mw"])
                q = float(self.network.res_sgen.at[elem, "q_mvar"])
        for elem in pp.toolbox.get_connected_elements(self.network, "asymmetric_sgen", bus):
            if self.network.asymmetric_sgen.at[elem, "name"] == name:
                res = self.network.res_asymmetric_sgen
                p = float(res.at[elem, "p_a_mw"] + res.at[elem, "p_b_mw"] + res.at[elem, "p_c_mw"])
                q = float(res.at[elem, "q_a_mvar"] + res.at[elem, "q_b_mvar"] + res.at[elem, "q_c_mvar"])
        return p, q, is_slack

    def get_bus(self, bus_name, snapshot):
        print("____get_bus____", flush=True)
        # print(self.buses)
        power_system = {}
        try:
            power_system["name"] = str(bus_name)
            p, q, is_slack = self.get_interface_pq(self.buses[bus_name])
            power_system["control"] = "Slack" if is_slack else "PQ"
            power_system["p"] = str(p)
            power_system["q"] = str(q)
            print("__getting vs __")
            if self.three_phase:
                power_system["v_mag_pu"] = str(self.network.res_bus_3ph.vm_a_pu[self.buses[bus_name]])
                power_system["v_ang"] = str(self.network.res_bus_3ph.va_a_degree[self.buses[bus_name]])
            else:
                power_system["v_mag_pu"] = str(self.network.res_bus.vm_pu[self.buses[bus_name]])
                power_system["v_ang"] = str(self.network.res_bus.va_degree[self.buses[bus_name]])
            # power_system["control"] = str("Slack")
        except Exception as e:
            print("failed to get bus system", flush=True)
            print(e)
        print("power_system", power_system)
        return power_system

    # todo: add parameterization for multiple observers
    def observe(self, snapshot):
        print("____observe____", flush=True)
        for bus in self.to_observe:
            topic = self.get_topic(bus)
            value = self.get_bus(bus, snapshot)
            msg = self.producer.produce(topic, value, timestamp=self.timeSync.currentLocalTime)
            self.timeSync.notifiyAboutSentMessage(topic)


    def get_topic(self, string):
        print("____get_topic____", flush=True)
        return ("provision.simulation." + self.scenarioID + ".energy.Bus." + self.instanceID + '.' + string).replace(" ",
                                                                                                                 "_")

    def extract_network(self, responsibility):
        print("____extract_network____", flush=True)
        indexes = []
        for bus in self.network.bus.iterrows():
            if self.network.bus.name[bus[0]] in responsibility:
                indexes.append(bus[0])
        self.network = pp.toolbox.select_subnet(self.network, indexes)

    def get_cuts(self, responsibility):
        print("____get_cuts____", flush=True)
        indexes = []
        for bus in self.network.bus.iterrows():
            if self.network.bus.name[bus[0]] in responsibility:
                indexes.append(bus[0])
        for bus in indexes:
            for elem in pp.toolbox.get_connected_buses(self.network, bus):
                if elem not in indexes:
                    self.buses_at_cut.append(self.network.bus.name[bus])

    def create_interface(self):
        print("____create_interface____", flush=True)
        for bus in self.network.bus.iterrows():
            if self.network.bus.name[bus[0]] in self.buses_at_cut:
                if not pp.toolbox.get_connected_elements(self.network, "ext_grid", bus[0]):
                    pp.create_sgen(self.network, bus[0], p_mw=0, name=self.interface_sgen_name(bus[0]))

    def destroy(self):
        """Destroys all actors"""
        print("todo: destroy()")

    def write_results(self):
        print("____write_results____", flush=True)
        bus_rows = []
        line_rows = []

        for values in self.network.bus.iterrows():
            bus_id = values[0]
            if self.three_phase:
                v_mag = self.network.res_bus_3ph.vm_a_pu[values[0]]
                v_ang = self.network.res_bus_3ph.va_a_degree[values[0]]
            else:
                v_mag = self.network.res_bus.vm_pu[values[0]]
                v_ang = self.network.res_bus.va_degree[values[0]]
            bus_rows.append({
                "bus": bus_id,
                "v_mag": v_mag,
                "v_ang": v_ang
            })

        for values in self.network.line.iterrows():
            if self.three_phase:
                p0 = self.network.res_line_3ph.p_a_from_mw[values[0]]
                q0 = self.network.res_line_3ph.q_a_from_mvar[values[0]]
            else:
                p0 = self.network.res_line.p_from_mw[values[0]]
                q0 = self.network.res_line.q_from_mvar[values[0]]
            line_id = values[0]
            line_rows.append({
                "line": line_id,
                "p0": p0,
                "q1": q0
            })

        df_bus = pd.DataFrame(bus_rows)
        df_line = pd.DataFrame(line_rows)

        with pd.ExcelWriter(result_dir(self.scenarioID, self.instanceID) / "results.xlsx",
                            engine="openpyxl") as writer:
            df_bus.to_excel(writer, sheet_name="Bus", index=False)
            df_line.to_excel(writer, sheet_name="Line", index=False)
