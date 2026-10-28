"""Quasi-static OpenDSS adapter. All DaceDSX times are integer milliseconds."""
import csv
import json
import math
from pathlib import Path

from opendssdirect import dss


def finite(value):
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("Electrical values must be finite")
    return value


class OpenDSSAPI:
    def __init__(self, circuit_path, parameters=None, observers=None, output_path=None):
        self.circuit_path = Path(circuit_path).resolve(strict=True)
        self.parameters = parameters or {}
        self.observers = observers or []
        self.output_path = Path(output_path) if output_path else None
        self.engine = dss.NewContext()
        self.results = []
        self.time_ms = None
        self.converged = False
        self.publish_periods = {}
        self.inputs = json.loads(self.parameters.get("inputs", "[]"))
        self.profiles = json.loads(self.parameters.get("load_profiles", "[]"))
        self.phase = int(self.parameters.get("voltage_phase", "1"))
        if self.phase not in (1, 2, 3):
            raise ValueError("voltage_phase must be 1, 2, or 3")
        unknown = set(self.parameters) - {"inputs", "load_profiles", "voltage_phase"}
        if unknown:
            raise ValueError(f"Unsupported OpenDSS parameters: {sorted(unknown)}")

    def init(self, responsibilities):
        if responsibilities != ["*"]:
            raise ValueError("This adapter runs a complete circuit; responsibilities must be ['*']")
        e = self.engine
        e.Basic.AllowChangeDir(False)
        e(f'Compile "{self.circuit_path}"')
        if not e.Circuit.Name():
            raise ValueError("The Network resource did not create a circuit")
        e("Set mode=snapshot")
        self.buses = {b.lower(): b for b in e.Circuit.AllBusNames()}
        self.elements = {n.lower() for n in e.Circuit.AllElementNames()}
        for observer in self.observers:
            if (observer["task"] != "publish" or observer["element"] != "bus"
                    or observer["trigger"] != "" or observer["type"] != "avro"):
                raise ValueError("Observers require publish/bus, type avro, and an empty trigger")
            period = observer["period"]
            if not isinstance(period, int) or period < 0:
                raise ValueError("Observer period must be a nonnegative number of milliseconds")
            names = list(self.buses) if observer["filter"].strip() == "*" else [
                b.strip().lower() for b in observer["filter"].split(",")]
            for name in names:
                if name not in self.buses:
                    raise ValueError(f"Unknown observed bus: {name}")
                self.publish_periods.setdefault(name, set()).add(period)
        if not isinstance(self.inputs, list) or not isinstance(self.profiles, list):
            raise ValueError("inputs and load_profiles must be JSON arrays")
        targets = set()
        for spec in self.inputs:
            self._validate_target(spec)
            if not isinstance(spec.get("topic"), str) or not spec["topic"]:
                raise ValueError("Every input needs an exact Kafka topic")
            if spec["element"].lower() in targets:
                raise ValueError("An element may have only one input writer")
            targets.add(spec["element"].lower())
        for spec in self.profiles:
            self._validate_target({**spec, "quantity": "power"})
            target = spec["element"].lower()
            if target in targets:
                raise ValueError("An element may have only one profile or input writer")
            targets.add(target)
            points = spec.get("points", [])
            if not points:
                raise ValueError("Load profiles need time_ms/kw/kvar points")
            last = -1
            for point in points:
                t = point["time_ms"]
                if type(t) is not int or t < 0 or t <= last:
                    raise ValueError("Profile times must be increasing nonnegative integer milliseconds")
                finite(point["kw"])
                finite(point["kvar"])
                last = t

    def _validate_target(self, spec):
        element = spec["element"].lower()
        prefix = {"power": "load.", "voltage": "vsource."}.get(spec["quantity"])
        if prefix is None or not element.startswith(prefix) or element not in self.elements:
            raise ValueError(f"Invalid {spec['quantity']} input target: {element}")

    def apply_input(self, spec, value):
        """Bus records: positive net injection in MW/Mvar; angles in radians."""
        e = self.engine
        name = spec["element"].split(".", 1)[1]
        if spec["quantity"] == "power":
            # A neighbour's positive export becomes a negative load (injection).
            e.Loads.Name(name)
            e.Loads.kW(-1000 * finite(value["p"]))
            e.Loads.kvar(-1000 * finite(value["q"]))
        else:
            pu = finite(value["v_mag_pu"])
            if pu <= 0:
                raise ValueError("Source voltage must be positive")
            e.Vsources.Name(name)
            e.Vsources.PU(pu)
            e.Vsources.AngleDeg(math.degrees(finite(value["v_ang"])))

    def solve(self, time_ms):
        self.converged = False
        self.time_ms = time_ms
        self.engine.Solution.DblHour(time_ms / 3_600_000)
        for spec in self.profiles:
            eligible = [p for p in spec["points"] if p["time_ms"] <= time_ms]
            if eligible:
                point = eligible[-1]
                self.engine.Loads.Name(spec["element"].split(".", 1)[1])
                self.engine.Loads.kW(finite(point["kw"]))
                self.engine.Loads.kvar(finite(point["kvar"]))
        self.engine.Solution.Solve()
        self.converged = bool(self.engine.Solution.Converged())
        if not self.converged:
            raise RuntimeError(f"OpenDSS did not converge at {time_ms} ms")

    def get_bus(self, bus_name):
        if not self.converged:
            raise RuntimeError("No converged solution is available")
        name = bus_name.lower()
        if name not in self.buses:
            raise ValueError(f"Unknown bus: {bus_name}")
        e = self.engine
        e.Circuit.SetActiveBus(name)
        nodes = e.Bus.Nodes()
        if self.phase not in nodes or e.Bus.kVBase() <= 0:
            raise ValueError(f"Bus {name} needs phase {self.phase} and a voltage base")
        voltage = e.Bus.puVmagAngle()
        idx = nodes.index(self.phase) * 2
        magnitude, angle = voltage[idx], math.radians(voltage[idx + 1])
        # Sum PC-element terminal injections, not line/transformer through-flows.
        # OpenDSS Powers() is positive into the element, hence the minus sign.
        pc_elements = e.Bus.AllPCEatBus()
        p = q = 0.0
        slack = False
        for element in pc_elements:
            e.Circuit.SetActiveElement(element)
            if not e.CktElement.Enabled():
                continue
            powers = e.CktElement.Powers()
            conductors = e.CktElement.NumConductors()
            for terminal, bus in enumerate(e.CktElement.BusNames()):
                if bus.split(".", 1)[0].lower() != name:
                    continue
                start = 2 * terminal * conductors
                p -= sum(powers[start:start + 2 * conductors:2]) / 1000
                q -= sum(powers[start + 1:start + 2 * conductors:2]) / 1000
                slack |= element.lower().startswith("vsource.")
        return {"name": name, "p": str(finite(p)), "q": str(finite(q)),
                "v_mag_pu": str(finite(magnitude)), "v_ang": str(finite(angle)),
                "control": "Slack" if slack else "PQ"}

    def observations(self, start_ms):
        observations = {}
        for bus, periods in self.publish_periods.items():
            if any(period == 0 or (self.time_ms - start_ms) % period == 0 for period in periods):
                value = self.get_bus(bus)
                observations[bus] = value
                self.results.append({"time_ms": self.time_ms, **value})
        return observations

    def write_results(self):
        if self.output_path is None:
            raise ValueError("No results path configured")
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.output_path.with_suffix(".csv.tmp")
        with temporary.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=[
                "time_ms", "name", "p", "q", "v_mag_pu", "v_ang", "control"])
            writer.writeheader()
            writer.writerows(self.results)
        temporary.replace(self.output_path)
        return self.output_path

    def destroy(self):
        self.engine.Basic.ClearAll()
