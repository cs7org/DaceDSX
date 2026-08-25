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

import pvlib
import pandas as pd
import numpy as np

pd.options.mode.chained_assignment = None


class pvlibAPI(object):
    """ Class representing the surrounding environment """

    def __init__(self, timesync, producer, scenarioID, instanceID,
                 step_length=3600, simulationEnd=24, w="", wcb=None, to_observe=None, parameters=None):
        print("\n\n_____init_____\n\n", flush=True)

        if to_observe is None:
            to_observe = []
        self.wrapper_cb = wcb
        # self.consumer = consumer
        self.producer = producer
        self.scenarioID = scenarioID
        self.recOn = 0
        self.instanceID = instanceID
        self.step_length = step_length  # Timestep in sec
        self.simulation_time = simulationEnd * step_length  # simulation time in sec
        self.parameters = parameters
        print("HERE", flush=True)
        self.timeSync = timesync
        self.to_observe = to_observe
        self.buses_at_cut = []
        self.topicPre = "provision.simulation." + scenarioID + ".energy."
        self.pv_rows = []

    def init(self):

        print("PARAMETERS", self.parameters, flush=True)
        self.start_time = self.parameters["start_time"]
        self.end_time = self.parameters["end_time"]
        self.bus = self.parameters["bus"]
        self.topic = self.topicPre + "PV." + self.bus.replace(" ", "_")

        self.producer.create_topics([self.topic])

        latitude = 32.2
        longitude = -110.9
        self.location = pvlib.location.Location(latitude, longitude)

        self.freq = f"{self.step_length} min"

        # weather
        self.times = pd.date_range(
            self.start_time,
            self.end_time,
            freq=self.freq,
            tz="Etc/GMT+7",
        )


    def prepareStep(self, step):


        curr_time = pd.date_range(self.times[step], self.times[step+1], freq=self.freq)

        # Clear-sky irradiance
        clearsky = self.location.get_clearsky(curr_time)

        # Create a simple daily temperature cycle
        temp_air = 20 + 10 * np.sin(2 * np.pi * (curr_time.hour - 6) / 24)

        self.weather_subset = clearsky.copy()
        self.weather_subset["temp_air"] = temp_air
        self.weather_subset["wind_speed"] = 1

        # simple PV model
        module_parameters = dict(pdc0=1300000, gamma_pdc=-0.003)
        inverter_parameters = dict(pdc0=1200000)

        temperature_model_parameters = (
            pvlib.temperature.TEMPERATURE_MODEL_PARAMETERS["sapm"]
            ["open_rack_glass_glass"]
        )
        # create model chain

        temperature_model_parameters_sapm = (
            pvlib.temperature.TEMPERATURE_MODEL_PARAMETERS["sapm"]
            ["open_rack_glass_glass"]
        )

        system_sapm = pvlib.pvsystem.PVSystem(
            surface_tilt=30,
            surface_azimuth=180,
            module_parameters=module_parameters,
            inverter_parameters=inverter_parameters,
            temperature_model_parameters=temperature_model_parameters_sapm,
        )

        self.mc_sapm = pvlib.modelchain.ModelChain(
            system_sapm,
            self.location,
            dc_model="pvwatts",
            ac_model="pvwatts",
            temperature_model="sapm",
            aoi_model="no_loss",
        )

    def step(self, step):
        self.mc_sapm.run_model(self.weather_subset)
        self.log_results(step)


# TODO
    def processStep(self):
        value = self.get_pv(self.mc_sapm.results.ac.iloc[-1])
        print("Writing msg: ", value, self.topic, flush=True)
        msg = self.producer.produce(self.topic, value)
        self.timeSync.notifiyAboutSentMessage(self.topic)

    def postStep(self, step, timeInMS=0):
        pass

#TODO
    def get_pv(self, p_ac):
        pv_system = {}
        try:
            pv_system["power_ac"] = float(p_ac)
        except Exception as e:
            print("failed to get pv system", flush=True)
            print(e)
        return pv_system

    def destroy(self):
        """Destroys all actors"""
        print("todo: destroy()")

    def log_results(self, step):
        for values in self.mc_sapm.results.ac:
            # time = values[0]
            self.pv_rows.append({
                "bus": self.bus,
                "time": self.times[step],
                "p_ac": values
            })

    def write_results(self):

            df_bus = pd.DataFrame(self.pv_rows)
            for col in df_bus.select_dtypes(include=["datetimetz"]).columns:
                df_bus[col] = df_bus[col].dt.tz_localize(None)

            with pd.ExcelWriter(f"powerflow_results_{self.scenarioID}_{self.instanceID}.xlsx",
                                engine="openpyxl") as writer:
                df_bus.to_excel(writer, sheet_name="Bus", index=False)
