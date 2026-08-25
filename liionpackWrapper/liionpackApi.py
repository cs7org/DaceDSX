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
import time



class liionpackAPI(object):
    """ Class representing the surrounding environment """

    def __init__(self, timesync, consumer, producer, scenarioID, instanceID,
                 step_length=3600, simulationEnd=24, w="", wcb=None, to_observe=None, parameters=[]):
        # print("\n\n_____init_____\n\n", flush=True)
        if to_observe is None:
            to_observe = []
        self.wrapper_cb = wcb
        self.consumer = consumer
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
        # self.topic = self.topicPre + "battery." + self.bus

        # self.producer.create_topics([self.topic])

        # -------------------------
        # PACK PARAMETER
        # -------------------------
        self.Np = 134  # series cells
        self.Ns = 1  # parallel strings

        # Zellmodell (DFN = Doyle-Fuller-Newman)
        self.parameter_values = pybamm.ParameterValues("Chen2020")

        # -------------------------
        # PACK LAYOUT
        # -------------------------
        # 1D string layout
        I_mag = 5.0
        OCV_init = 4.0  # used for intial guess
        Ri_init = 5e-2  # used for intial guess
        R_busbar = 1.5e-3
        R_connection = 1e-2
        Np = 134
        Ns = 200
        self.Nbatt = Np * Ns
        self.netlist = lp.setup_circuit(
            Np=Np, Ns=Ns, Rb=R_busbar, Rc=R_connection, Ri=Ri_init, V=OCV_init, I=I_mag
        )

        # self.bus = self.parameters["bus"]
        # self.slack = self.parameters["slack"]
        self.bus_topic = self.topicPre + "Battery." + self.bus.replace(" ", "_")
        slack_topic = self.topicPre + "Battery."+ self.slack.replace(" ", "_")
        self.producer.create_topics([self.bus_topic, slack_topic])
        print("HERE before subscribing to slack topic")
        self.consumer.subscribe([slack_topic])
        print("HERE after subscribing to slack topic")
        self.wait_for_topic(slack_topic)

    def wait_for_topic(self, topic, timeout=10):
        start = time.time()
        while time.time() - start < timeout:
            meta = self.consumer.list_topics()
            print(meta.keys(), topic, topic in meta.keys(), flush=True)
            if topic in meta.keys():
                return True
            time.sleep(0.5)
        return False

    def prepareStep(self, step):
        # -------------------------
        # EXCITATION PROFILE
        # -------------------------
        print("HERE in prepare step", flush=True)
        msg = self.consumer.poll(5)
        if msg:
            power = msg.value()['power']
            if abs(power) > 255601:
                power = 0.000000005
        else:
            power = 0.000000005

        if power < 0:
            self.protocol = [
                f"Discharge at {abs(power)} W for {self.step_length} min",
            ]
        elif power > 0:
            self.protocol = [
            f"Charge at {abs(power)} W for {self.step_length} min",
            ]
        else:
            self.protocol = [
            f"Discharge at {power} W  for {self.step_length} min",
            ]
        return power

    def step(self, step):
        # 5. Perform the simulation
        print("______step______", self.protocol)
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
        self.curr_soc= (self.curr_soc*24000-power)/24000
        value = self.get_bat(self.output)
        msg = self.producer.produce(self.bus_topic, value)
        self.timeSync.notifiyAboutSentMessage(self.bus_topic)

    def postStep(self, step, timeInMS=0):
        pass

#TODO
    def get_bat(self, output):
        battery_system = {}
        try:
            battery_system["power"] = float(output["Pack power [W]"][-1])
            battery_system["current"] = str(output["Pack current [A]"][-1])
            battery_system["voltage"] = str(output["Pack terminal voltage [V]"][-1])
            battery_system["soc"] = str(self.curr_soc)
        except Exception as e:
            print("failed to get battery system", flush=True)
            print(e)
        return battery_system

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
