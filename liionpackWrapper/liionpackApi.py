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

import liionpack as lp
import pybamm
import pandas as pd
import numpy as np
import math
import time
from MessageBuffer import MessageBuffer



class liionpackAPI(object):
    """ Class representing the surrounding environment """

    def __init__(self, timesync, producer, scenarioID, instanceID,
                 step_length=3600, simulationEnd=24, w="", wcb=None, to_observe=None, parameters=[]):
        # print("\n\n_____init_____\n\n", flush=True)
        if to_observe is None:
            to_observe = []
        self.wrapper_cb = wcb
        # filled by the wrapper's main consumer thread, read in prepareStep
        self.inbox = MessageBuffer()
        self.producer = producer
        self.scenarioID = scenarioID
        self.recOn = 0
        self.instanceID = instanceID
        self.step_length = step_length  # Timestep in sec
        self.simulation_time = simulationEnd * step_length  # simulation time in min
        self.parameters = parameters

        self.timeSync = timesync
        self.to_observe = to_observe
        self.buses_at_cut = []
        self.topicPre = "provision.simulation." + scenarioID + ".energy."
        self.pv_rows = []

    def init(self):
        self.bus = self.parameters["bus"]
        # self.ini_soc = self.parameters["soc"]
        self.curr_soc = float(self.parameters["soc"])
        self.slack = self.parameters["slack"]
        # maximum charge/discharge power [W]. Requests above are limited to it instead of being ignored.
        # 255601 W was the old cut-off value, so it stays the default when the scenario sets none
        self.p_max = float(self.parameters.get("p_max", 255601))
        # self.topic = self.topicPre + "battery." + self.bus

        # self.producer.create_topics([self.topic])

        # -------------------------
        # PACK PARAMETER
        # -------------------------
        # liionpack convention: Np = cells in parallel, Ns = cells in series
        self.Np = 134
        self.Ns = 200

        # Zellmodell (DFN = Doyle-Fuller-Newman)
        self.parameter_values = pybamm.ParameterValues("Chen2020")
        # pack capacity for the SoC bookkeeping (coulomb counting)
        self.capacity_ah = self.Np * float(self.parameter_values["Nominal cell capacity [A.h]"])
        self.voltage = 0.0  # last known pack voltage

        # -------------------------
        # PACK LAYOUT
        # -------------------------
        # 1D string layout
        I_mag = 5.0
        OCV_init = 4.0  # used for intial guess
        Ri_init = 5e-2  # used for intial guess
        R_busbar = 1.5e-3
        R_connection = 1e-2
        self.Nbatt = self.Np * self.Ns
        self.netlist = lp.setup_circuit(
            Np=self.Np, Ns=self.Ns, Rb=R_busbar, Rc=R_connection, Ri=Ri_init, V=OCV_init, I=I_mag
        )

        # self.bus = self.parameters["bus"]
        # self.slack = self.parameters["slack"]
        self.bus_topic = self.topicPre + "Battery." + self.bus.replace(" ", "_")
        self.slack_topic = self.topicPre + "Battery."+ self.slack.replace(" ", "_")
        self.producer.create_topics([self.bus_topic, self.slack_topic])

    def on_msg(self, inMsg):
        """Called by processMsg of the wrapper"""
        self.inbox.add(inMsg)

    def prepareStep(self, step):
        # -------------------------
        # EXCITATION PROFILE
        # -------------------------
        print("HERE in prepare step", flush=True)
        # TimeSync guarantees that all messages sent before the current time have arrived,
        # messages of the current step stay buffered for the next one
        msgs = self.inbox.take(self.timeSync.currentLocalTime, topic=self.slack_topic)
        # drop messages on other Battery.* topics (e.g. our own output), they are only counted
        self.inbox.take(self.timeSync.currentLocalTime)
        msg = msgs[-1] if msgs else None

        # sign convention (same as the liionpack output and pandapower sgens):
        # power > 0 = discharge (feed into the grid), power < 0 = charge
        power = 0.0
        if msg:
            requested = float(msg.value()['power'])
            if math.isnan(requested):
                print("received NaN power, battery rests", flush=True)
            else:
                power = max(-self.p_max, min(self.p_max, requested))
                if power != requested:
                    print("requested", requested, "W, limited to", power, "W (p_max)", flush=True)

        if power > 0:
            self.protocol = [
                f"Discharge at {power} W for {self.step_length} min",
            ]
        elif power < 0:
            self.protocol = [
            f"Charge at {-power} W for {self.step_length} min",
            ]
        else:
            # liionpack only supports current and power steps, no "Rest"
            self.protocol = [
            f"Discharge at 0 A for {self.step_length} min",
            ]
        return power

    def step(self, step):
        # 5. Perform the simulation
        print("______step______", self.protocol)
        # no stale result from the previous step if the solver fails
        self.output = None
        self.output = lp.solve(
            netlist=self.netlist,
            parameter_values=self.parameter_values,
            experiment=pybamm.Experiment(self.protocol, period=f"{self.step_length} min"),
            # experiment=pybamm.Experiment(self.protocol, period=f"1 min"),
            output_variables=["Terminal voltage [V]"],
            initial_soc=self.curr_soc
        )
        self.log_results(step)


# TODO
    def processStep(self, power):
        value = self.get_bat(self.output)
        msg = self.producer.produce(self.bus_topic, value, timestamp=self.timeSync.currentLocalTime)
        self.timeSync.notifiyAboutSentMessage(self.bus_topic)
        self.pv_rows.append({"time": self.timeSync.currentLocalTime, "requested_power": power, **value})

    def postStep(self, step, timeInMS=0):
        pass

    @staticmethod
    def integrate(y, t):
        """Trapezoidal integral of y over t, 0 for a single sample"""
        y, t = np.asarray(y, dtype=float), np.asarray(t, dtype=float)
        if len(t) < 2:
            return 0.0
        return float(np.sum((y[1:] + y[:-1]) / 2 * np.diff(t)))

    def get_bat(self, output):
        """
        Updates the SoC from this step's solver output and returns the message for Battery.avsc.
        power/current are averages over the whole step (energy and charge divided by the step length),
        so a step the solver stopped early (voltage limit) only counts with the time it actually ran.
        """
        step_s = self.step_length * 60
        if output is None:
            print("no battery result for this step, reporting rest", flush=True)
            charge_ah, energy_j = 0.0, 0.0
        else:
            t = output["Time [s]"]
            charge_ah = self.integrate(output["Pack current [A]"], t) / 3600
            energy_j = self.integrate(output["Pack power [W]"], t)
            self.voltage = float(output["Pack terminal voltage [V]"][-1])
            simulated_s = float(t[-1] - t[0]) if len(t) > 1 else 0.0
            if simulated_s < step_s:
                print(f"battery solver stopped after {simulated_s:.0f} of {step_s} s (voltage limit?)", flush=True)

        # coulomb counting, discharge current is positive
        self.curr_soc = min(1.0, max(0.0, self.curr_soc - charge_ah / self.capacity_ah))

        # all fields are "float" in Battery.avsc, strings make the Avro serializer reject the message
        return {
            "power": energy_j / step_s,
            "current": charge_ah * 3600 / step_s,
            "voltage": self.voltage,
            "soc": float(self.curr_soc),
        }

    def destroy(self):
        """Destroys all actors"""
        print("todo: destroy()")

    def log_results(self, step):
        pass
        # for values in self.curr_soc:
        #     time = values[0]
        #     self.pv_rows.append({
        #         "bus": self.bus,
        #         "time": step,
        #         "p_ac": values
        #     })

    def write_results(self):
            df_bus = pd.DataFrame(self.pv_rows)
            with pd.ExcelWriter(f"powerflow_results_{self.scenarioID}_{self.instanceID}.xlsx",
                                engine="openpyxl") as writer:
                df_bus.to_excel(writer, sheet_name="Bus", index=False)
