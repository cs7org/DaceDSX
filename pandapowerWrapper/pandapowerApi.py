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
from MessageBuffer import MessageBuffer, collectPeerMsgs
from ResultDir import result_dir

pd.options.mode.chained_assignment = None

# boundary values at the copy buses count as unchanged below this difference (pu, degree, MW, MVAr)
COUPLING_TOL = 1e-6
COUPLING_MAX_ITERATIONS = 50


class pandapowerAPI(object):
    """ Class representing the surrounding environment """

    def __init__(self, network_path, timesync, consumer, producer, scenarioID, other_instance_topics, instanceID,
                 step_length=3600, simulationEnd=24, w="", wcb=None, to_observe=None, parameters=[], peers=None):
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
        # power flow results per step, written by write_results
        self.bus_rows = []
        self.line_rows = []

        self.timeSync = timesync
        self.to_observe = to_observe
        self.buses_at_cut = []
        # other power flow instances and the buses they couple at, from the scenario
        self.peers = peers or {}
        # topics of other power flow instances at the copy buses, set in init
        self.ghost_topics = []

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
        # the peers' topics are known from the scenario, creating them here as well makes the
        # subscription independent of which instance starts first
        self.ghost_topics = [self.get_peer_topic(peer, bus) for bus in self.buses_at_cut
                             for peer, buses in self.peers.items() if bus in buses]
        topics_to_create += self.ghost_topics
        print("topics_to_create",topics_to_create)
        print("ghost_topics", self.ghost_topics)
        if topics_to_create:
            self.producer.create_topics(topics_to_create)
        if self.ghost_topics:
            self.consumer.subscribe(self.ghost_topics)
        self.buses = {}
        for bus in self.network.bus.iterrows():
            self.buses[self.network.bus.name[bus[0]]] = bus[0]

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
            # counted for the sync barrier by producer.on_sent (set in pandapowerWrapper)
            msg = self.producer.produce(topic, value, timestamp=self.timeSync.currentLocalTime)
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
        self.log_results(step)

    def log_results(self, step):
        """Stores the power flow result of the current time; a repeated power flow in the same step
        (see postStep) replaces the rows of the earlier one."""
        t = self.timeSync.currentLocalTime
        self.bus_rows = [r for r in self.bus_rows if r["time"] != t]
        self.line_rows = [r for r in self.line_rows if r["time"] != t]
        if self.three_phase:
            res_bus, vm, va, p, q = self.network.res_bus_3ph, "vm_a_pu", "va_a_degree", "p_a_mw", "q_a_mvar"
            res_line, lp, lq = self.network.res_line_3ph, "p_a_from_mw", "q_a_from_mvar"
        else:
            res_bus, vm, va, p, q = self.network.res_bus, "vm_pu", "va_degree", "p_mw", "q_mvar"
            res_line, lp, lq = self.network.res_line, "p_from_mw", "q_from_mvar"
        for idx in self.network.bus.index:
            self.bus_rows.append({
                "time": t,
                "bus": idx,
                "name": self.network.bus.at[idx, "name"],
                "v_mag": res_bus.at[idx, vm],
                "v_ang": res_bus.at[idx, va],
                "p": res_bus.at[idx, p],
                "q": res_bus.at[idx, q]
            })
        for idx in self.network.line.index:
            self.line_rows.append({
                "time": t,
                "line": idx,
                "name": self.network.line.at[idx, "name"],
                "p0": res_line.at[idx, lp],
                "q1": res_line.at[idx, lq]
            })

    def postStep(self, step, timeInMS=0):
        """
        Couples the copy buses with the other power flow instances (peers): applies their latest
        boundary values, repeats the power flow and publishes the result as long as something
        changes. A side without changes stays silent, the exchange ends when nothing new arrives.
        """
        print("___postStep___", flush=True)
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
        A copy bus with an ext_grid takes the voltage of the peer, otherwise the interface sgen
        takes the power: what the peers inject into their part leaves this one.
        """
        changed = False
        for copy_bus in self.buses_at_cut:
            values = [m.value() for m in msgs if m.value()['name'] == copy_bus]
            if not values:
                continue
            bus = self.buses[copy_bus]
            ext = list(pp.toolbox.get_connected_elements(self.network, "ext_grid", bus))
            if ext:
                # the voltage comes from a peer that computes it, not from another slack
                v = next((x for x in values if x['control'] != "Slack"), values[-1])
                new = (float(v['v_mag_pu']), float(v['v_ang']))
                old = (self.network.ext_grid.at[ext[0], "vm_pu"], self.network.ext_grid.at[ext[0], "va_degree"])
            else:
                new = (-sum(float(x['p']) for x in values), -sum(float(x['q']) for x in values))
                old = self.get_interface_setpoint(bus)
            print("copy bus", copy_bus, "slack" if ext else "pq", "old", old, "new", new, flush=True)
            if any(abs(a - b) > COUPLING_TOL for a, b in zip(old, new)):
                v_mag, v_ang = new if ext else (0, 0)
                p, q = (0, 0) if ext else new
                self.set_values_pp(bool(ext), bus, v_mag, v_ang, p, q)
                changed = True
        return changed

    def get_interface_setpoint(self, bus):
        """p [MW] / q [MVAr] set at the interface sgen of a copy bus (bus = bus index)"""
        name = self.interface_sgen_name(bus)
        for elem in pp.toolbox.get_connected_elements(self.network, "sgen", bus):
            if self.network.sgen.at[elem, "name"] == name:
                return self.network.sgen.at[elem, "p_mw"], self.network.sgen.at[elem, "q_mvar"]
        for elem in pp.toolbox.get_connected_elements(self.network, "asymmetric_sgen", bus):
            if self.network.asymmetric_sgen.at[elem, "name"] == name:
                sg = self.network.asymmetric_sgen
                return (sum(sg.at[elem, f"p_{ph}_mw"] for ph in "abc"),
                        sum(sg.at[elem, f"q_{ph}_mvar"] for ph in "abc"))
        return 0.0, 0.0

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
            # counted for the sync barrier by producer.on_sent (set in pandapowerWrapper)
            msg = self.producer.produce(topic, value, timestamp=self.timeSync.currentLocalTime)


    def get_topic(self, string):
        print("____get_topic____", flush=True)
        return self.get_peer_topic(self.instanceID, string)

    def get_peer_topic(self, instanceID, bus):
        """Topic on which instanceID publishes its values at a copy bus"""
        return ("provision.simulation." + self.scenarioID + ".energy.Bus." + instanceID + '.' + bus).replace(" ", "_")

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
        df_bus = pd.DataFrame(self.bus_rows)
        df_line = pd.DataFrame(self.line_rows)

        with pd.ExcelWriter(result_dir(self.scenarioID, self.instanceID) / "results.xlsx",
                            engine="openpyxl") as writer:
            df_bus.to_excel(writer, sheet_name="Bus", index=False)
            df_line.to_excel(writer, sheet_name="Line", index=False)
