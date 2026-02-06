from pathlib import Path
import pandas as pd
import numpy as np
import pandapower as pp
import json

pd.options.mode.chained_assignment = None


class pandapowerAPI:
    def __init__(self, network_path, step_length=3600, n_steps=24, out_dir="results"):
        self.network_path = network_path
        self.step_length = step_length
        self.n_steps = int(n_steps)
        self.out_dir = out_dir
        self.network = None
        self.load_profile = None
        self.sgen_profile = None
        self.bus_vm = None
        self.bus_va = None
        self.line_p = None
        self.trafo_p = None
        self.history = []

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

    def init(self):
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
                try: self.load_profile.index = self.load_profile.index.astype(int)
                except: pass

        if sgen_csv.exists():
            self.sgen_profile = pd.read_csv(sgen_csv, index_col=0)
        elif sgen_json.exists():
            self.sgen_profile = pd.read_json(sgen_json)
            if not self.sgen_profile.empty:
                try: self.sgen_profile.index = self.sgen_profile.index.astype(int)
                except: pass

        bus_names = [str(n) if pd.notna(n) else f"bus_{i}" for i, n in enumerate(self.network.bus.get('name', []))]
        if not bus_names:
            bus_names = [f"bus_{i}" for i in self.network.bus.index]
        
        line_names = [f"line_{i}" for i in self.network.line.index]
        trafo_names = [f"trafo_{i}" for i in self.network.trafo.index] if hasattr(self.network, 'trafo') else []
        
        self.bus_vm = pd.DataFrame(index=range(self.n_steps), columns=bus_names, dtype=float)
        self.bus_va = pd.DataFrame(index=range(self.n_steps), columns=bus_names, dtype=float)
        self.line_p = pd.DataFrame(index=range(self.n_steps), columns=line_names, dtype=float)
        self.trafo_p = pd.DataFrame(index=range(self.n_steps), columns=trafo_names, dtype=float)

    def prepareStep(self, step):
        if self.load_profile is not None and step in self.load_profile.index:
            for col, val in self.load_profile.loc[step].items():
                if pd.notna(val):
                    try:
                        idx = int(col) if str(col).isdigit() else None
                        if idx is not None and idx in self.network.load.index:
                            self.network.load.at[idx, 'p_mw'] = float(val)
                    except: pass

        if self.sgen_profile is not None and step in self.sgen_profile.index:
            for col, val in self.sgen_profile.loc[step].items():
                if pd.notna(val):
                    try:
                        idx = int(col) if str(col).isdigit() else None
                        if idx is not None and idx in self.network.sgen.index:
                            self.network.sgen.at[idx, 'p_mw'] = float(val)
                    except: pass

    def step(self, step):
        try:
            pp.runpp(self.network)
        except Exception as e:
            print(f"Powerflow failed at step {step}: {e}")
        
        for i, idx in enumerate(self.network.bus.index):
            col = self.bus_vm.columns[i]
            try:
                self.bus_vm.at[step, col] = self.network.res_bus.at[idx, 'vm_pu']
                self.bus_va.at[step, col] = self.network.res_bus.at[idx, 'va_degree']
            except: pass
        
        for i, idx in enumerate(self.network.line.index):
            col = self.line_p.columns[i]
            try: self.line_p.at[step, col] = self.network.res_line.at[idx, 'p_from_mw']
            except: pass
        
        if hasattr(self.network, 'res_trafo'):
            for i, idx in enumerate(self.network.trafo.index):
                col = self.trafo_p.columns[i]
                try: self.trafo_p.at[step, col] = self.network.res_trafo.at[idx, 'p_hv_mw']
                except: pass

        self.history.append({'step': step})

    def export_results(self, out_dir=None):
        out = Path(out_dir or self.out_dir)
        out.mkdir(parents=True, exist_ok=True)
        
        self.bus_vm.to_csv(out / "bus_vm_pu.csv", index_label="step")
        self.bus_va.to_csv(out / "bus_va_degree.csv", index_label="step")
        self.line_p.to_csv(out / "line_p_from_mw.csv", index_label="step")
        self.trafo_p.to_csv(out / "trafo_p_mw.csv", index_label="step")
        
        with open(out / "history.json", "w") as f:
            json.dump(self.history, f, indent=2)
