import glob
import numpy as np
import gym
import os
import sys
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("please declare environment variable 'SUMO_HOME'")

import traci
import math
from gym import spaces
from typing import List, TypeVar, Tuple, cast
import getopt
import os
import sys
import time
import Backend as Backend
import FleetManager as fleetManager
import V2VNetworkingLayer as v2vNetworkingLayer
import csv
import pathlib
import traceback
import random
import parameter_parser
import ISMNetworkingLayer as ismNetworkingLayer
import WlanAPManager as wlan_ap_manager

import shutil
ObsType = TypeVar("ObsType")
ActType = TypeVar("ActType")


class env_v4(gym.Env):

    def get_data_rate(self, communication_standard: str, mcs: int, dcm: bool = False) -> float:
        """
        returns data rate belonging to communication standard and mcs combination
        @param communication_standard: the used standard
        @param mcs: mcs index
        @return: data rate in Byte/s
        """
        if communication_standard == "bd":
            # coderate and number of bits per symbol
            packetsize = 1500
            cr_nbps = {
                0: (0.5, 1),
                1: (0.5, 2),
                2: (0.75, 2),
                3: (0.5, 4),
                4: (0.75, 4),
                5: (2 / 3, 6),
                6: (0.75, 6),
                7: (5 / 6, 6),
                8: (3 / 4, 8),
                9: (5 / 6, 8),
            }
            cr = cr_nbps[mcs][0]
            nbps = cr_nbps[mcs][1]
            if dcm: nbps = nbps / 2
            nsym = math.ceil((packetsize * 8) / (52 * cr * nbps))
            if mcs < 5:
                tma = 8
            else:
                tma = 4
            nma = math.floor((nsym - 1) / tma)
            tx = 80 + 32 + 8 * nsym + 8 * nma
            tx = round(tx * 10 ** -3, 3)
            data_rate = round(((packetsize * 8) / (tx * 10 ** -3)) * 10 ** -6, 2)
        else:
            standards = {  # in Mbps
                "p": {
                    0: 2.94,
                    1: 4.37,
                    2: 5.77,
                    3: 8.52,
                    4: 11.19,
                    5: 16.13,
                    6: 20.83,
                    7: 23.08
                },
                "bd": {
                    0: 3.02,
                    1: 5.93,
                    2: 8.72,
                    3: 11.41,
                    4: 16.57,
                    5: 20.13,
                    6: 22.22,
                    7: 24.19,
                    8: 28.30,
                    9: 30.92
                },
                "lte": {
                    0: 1.13,
                    6: 4.22,
                    7: 4.94,
                    10: 7.09,
                    13: 9.24,
                    17: 12.88,
                    21: 17.49,
                    27: 25.77
                },
                "nr": {
                    0: 1.70,
                    6: 6.31,
                    7: 7.36,
                    10: 9.57,
                    13: 13.67,
                    17: 19.80,
                    21: 27.34,
                    27: 38.27
                }
            }
            data_rate = standards[communication_standard][mcs]  # in Mbps
        return (data_rate * 10 ** 6) / 8  # in bit # should be byte

    def calculate_sinr_min(self, communication_standard: str, mcs: int, noisepower: int = 0, dcm: bool = False,
                           retr: bool = True) -> float:
        if communication_standard == "p" or communication_standard == "bd":
            min_input_sens = {
                0: -85,
                1: -84,
                2: -82,
                3: -80,
                4: -77,
                5: -73,
                6: -69,
                7: -68
            }
            sinr_min = min_input_sens[mcs] - noisepower
            if communication_standard == "bd":
                if mcs == 0:
                    sinr_min = min_input_sens[mcs] - noisepower
                else:
                    sinr_min = min_input_sens[mcs + 1] - noisepower
                sinr_min -= 3  # error correction, use of ldpc -> 3 db lower sensitivity
                if dcm: sinr_min -= 5  # dcm mode -> 5 db gain
                if retr: sinr_min -= 7  # adaptive retransmission -> 4-7 db
        else:
            if communication_standard == "lte":
                # data[0] = code_rate, data[1] = number bits per symbol
                data = {
                    0: (0.13, 2),
                    6: (0.47, 2),
                    7: (0.55, 2),
                    10: (0.81, 2),
                    13: (0.52, 4),
                    17: (0.75, 4),
                    21: (0.65, 6),
                    27: (0.93, 6)
                }
            elif communication_standard == "nr":
                # data[0] = code_rate, data[1] = number bits per symbol
                data = {
                    0: (0.12, 2),
                    6: (0.44, 2),
                    7: (0.51, 2),
                    10: (0.33, 4),
                    13: (0.48, 4),
                    17: (0.45, 6),
                    21: (0.65, 6),
                    27: (0.92, 6)
                }
            code_rate = data[mcs][0]
            nbps = data[mcs][1]
            bhz = (14 * 12 * nbps * code_rate) / 180
            res = 2 ** (bhz / (1 - 0.6)) - 1
            sinr_min = round(10 * math.log(res, 10), 1)
        return sinr_min

    def calc_eta(mcs: int, standard):
        if standard == "lte":
            nrb = {
                0: 434,
                6: 116,
                7: 99,
                10: 69,
                13: 53,
                17: 38,
                21: 28,
                27: 19
            }
            nrb_mcs = 2 * nrb[mcs]
        elif standard == "nr":
            nrb = {
                0: 337,
                6: 91,
                7: 78,
                10: 60,
                13: 42,
                17: 29,
                21: 21,
                27: 15
            }
            nrb_mcs = nrb[mcs]
        nsfr_message = math.ceil(nrb_mcs / 81)
        eta = (math.ceil(nrb_mcs / nsfr_message)) / 100
        return eta

    def calculate_communication_range(self, transmission_power: float, gain: int, noisepower: int, pathloss: float,
                                      loss_exponent: float, communication_standard: str, mcs: int) -> int:
        """
            calculates transmission range with several configuration values
            @param transmission_power: transmission_power in dBm
            @param gain: gain in dB
            @param noisepower: noisepower in dBm
            @param pathloss: pathloss in dB
            @param loss_exponent: loss_exponent as float
            @param communication_standard: used standard
            @param mcs: mcs index
            @return: achievable transmission range in m
        """
        sinr_min = self.calculate_sinr_min(communication_standard, mcs, noisepower)
        # sinr_min = -95 + 98
        if communication_standard == "lte" or communication_standard == "nr":
            eta = 10 * math.log(self.calc_eta(mcs, communication_standard), 10)
            range = 10 ** ((transmission_power + 2 * gain - (sinr_min + pathloss + eta + noisepower)) / 10)

        elif communication_standard == "p" or communication_standard == "bd":
            range = 10 ** ((transmission_power + 2 * gain - (sinr_min + pathloss + noisepower)) / 10)
            # print(sinr_min)
        range = range ** (1 / loss_exponent)
        # print(range)
        # range = 10 ** ((transmission_power + 2 * gain - (sinr_min + pathloss + noisepower)) / 10)
        # range = range ** (1 / 2)
        # print(range)
        # print(10 ** ((transmission_power + 2*gain - (sinr_min + pathloss + noisepower)) / 10))
        # print(10 ** ((transmission_power + 2 * gain - (-82 + pathloss)) / 10))
        # print(sinr_min, pathloss, noisepower)
        # print((sinr_min + pathloss + noisepower))
        # print(transmission_power + 2*gain - (sinr_min + pathloss + noisepower))
        # print((10 ** ((transmission_power + 2*gain - (sinr_min + (-1*pathloss) + noisepower)) / 10)))
        # print((10 ** (transmission_power + 2*gain - (-82 + (-1*pathloss) + noisepower)) / 10) ** (1 / loss_exponent))
        # sys.exit()
        # if communication_standard == "bd":
        #     range = range * 2
        return round(range)


    """
    chunksimulation RL Environment that follows gym interface.
    Agent should learn to find optimal initial seed number in terms
    of downloading costs caused by cellular communication.
    """
    def __init__(self):
        self.config = 'config_seeding_strategy_update2.xml'
        self.parameter_index = 0
        self.iteration_counter = 0
        self.out_csv_name = None
        self.info = {}
        self.episode = 0
        self.seed_v = 20008
        random.seed(self.seed_v)
        # parse parameters
        self.sumo_cfg, self.sumo_binary, self.number_vehicles, self.additional_vehicles, self.update_size, self.initial_seeds, self.v2v_distance, self.duration, \
            self.duration_parameter, self.output_abs_path, self.buildings_tuple, self.ap_placement, self.v2v_device, self.wlan_device, self.wlan_distance, \
            self.wlan_beacon_interval, self.v2v_heartbeat_interval, self.wlan_ap_count, self.wlan_heartbeat_strategy, self.v2v_heartbeat_strategy, \
            self.heartbeat_encoding, self.v2v_data_rate, self.wlan_data_rate, self.seeding_strategy, self.parameters, self.sumo_route, \
            self.communication_standard, self.mcs, self.additional_attenuation, self.ap_coords, self.max_number_connections, \
            self.v2v_equipment_percentage, self.wlan_equipment_percentage, self.wlan_ap_percentage \
            = parameter_parser.parse_parameter_xml(
            self.config, self.parameter_index)
        self.gain, self.transmission_power, self.pathloss, self.noisepower, self.loss_exponent, self.antenna_height, self.two_ray, self.log_distance, \
            self.log_shadow, self.shadow_slope, self.loss_exponent2, self.sigma, self.sigma2 = parameter_parser.parse_constants_xml(self.config)
        self.loss_exponent += self.additional_attenuation
        print(self.seeding_strategy)
        if self.communication_standard != "n/a":
            self.distance = self.calculate_communication_range(self.transmission_power, self.gain, self.noisepower, self.pathloss, self.loss_exponent,
                                                     self.communication_standard, self.mcs)

            print(self.distance)
            # sys.exit()
            # data_rate = get_data_rate(communication_standard, mcs)# / 5.0 #number_vehicles
            self.data_rate = 60000
            # print(data_rate)
            # sys.exit()
            # distance = 600  # 2 * distance
            self.v2v_distance = self.distance  # 300 #557 #distance
            self.v2v_data_rate = self.data_rate
        else:
            self.distance = None
            self.data_rate = None
        # Define variables for cost calculation
        self.chunk_size = 1411  # fixed chunk size inherited from simulation framework
        rand_val = random.randint(0, 100)
        rand_val = 100
        self.update_size = 1000000 * rand_val  # random.choice(data_sizes)
        self.update_index = rand_val  # data_sizes.index(self.update_size)

        if self.update_size % self.chunk_size != 0:
            self.max_chunks = int(self.update_size / self.chunk_size)+1
        else:
            self.max_chunks = int(self.update_size / self.chunk_size)
        print(self.update_size, self.update_index, self.max_chunks)
        #sys.exit()
        self.cost_value = 1 / self.max_chunks
        self.update_data = {}
        self.update_names = []
        self.time_done = 0
        self.total_seed = 0
        self.action_costs = 0

        # time parameters
        timelimit = self.duration_parameter
        self.timesteps = 8
        self.timestep_counter = 0
        self.seeding_time = int(timelimit / self.timesteps)

        # Define action and observation space (must be gym spaces objects)
        # Actions we can take:
        # 0 - 20 % seeding of full update
        self.action_size = 151
        self.action_space = spaces.Discrete(self.action_size)
        # Observations: All environment's data to be observed by agent
        # seeds at the end of download time
        #self.observation_space = spaces.Discrete(self.max_chunks+1)
        #state of update in simulation, number of seeded chunks
        self.observation_space = spaces.MultiDiscrete([1001, 1001, 1001, 101])
        # State: update_progress
        self.state = self.initial_seeds
        self.seed_size = 0.05
        
        self.reward = 0
        
        # create log dict
        self.log_dict = {}
        self.log_episode = {}
        self.connected_vehicles = []

        # close traci simulations
        try:
            traci.close()
        except:
            pass

        # create sumo environment
        pathlib.Path(self.output_abs_path).mkdir(parents=True, exist_ok=True)
        os.chdir(self.output_abs_path)
        sumo_cmd = [self.sumo_binary, "-c", self.sumo_cfg, "--seed", str(int(0)), "-S"]

        traci.start(sumo_cmd)
        self.traciStep = 0
        self.backend_server = Backend.Backend(self.chunk_size, self.initial_seeds, self.number_vehicles, self.seeding_strategy)
        self.v2v_layer = None
        self.ism_layer = None
        if self.v2v_device and self.v2v_equipment_percentage > 0.0:
            self.v2v_layer = v2vNetworkingLayer.V2VNetworkingLayer(traci, self.distance, self.data_rate,
                                                              self.gain, self.transmission_power,
                                                              self.pathloss, self.noisepower, self.loss_exponent, self.antenna_height,
                                                              self.two_ray, self.log_distance,
                                                              self.log_shadow, self.shadow_slope, self.loss_exponent2, self.sigma, self.sigma2
                                                              )

        if self.wlan_device and self.wlan_equipment_percentage > 0.0:
            self.ism_layer = ismNetworkingLayer.ISMNetworkingLayer(traci)
        t = time.time()
        var_dump_file_name = time.strftime("%d%m%Y%H_%M_%S") + "_" + str(
            int(round(t * 1000))) + "_%i_%i_%i" % (
                                 self.additional_vehicles, self.number_vehicles, self.duration_parameter)
        for value in self.parameters:
            if type(value) is float:
                var_dump_file_name += "_%i" % (int(value * 100))
            elif type(value) is str:
                var_dump_file_name += "_" + value.replace(' ', '_')
            else:
                var_dump_file_name += "_%i" % (int(value))
        var_dump_file_name += "_%i" % self.iteration_counter

        self.vehicle_fleet = fleetManager.FleetManager(traci, self.backend_server, self.v2v_layer, self.additional_vehicles,
                                                  self.number_vehicles,
                                                  self.duration_parameter, self.ism_layer, self.v2v_device, self.wlan_device,
                                                  self.wlan_heartbeat_strategy, self.v2v_heartbeat_strategy, self.heartbeat_encoding,
                                                  self.v2v_heartbeat_interval, self.v2v_distance, self.v2v_data_rate,
                                                  var_dump_file_name, self.duration, self.wlan_distance, self.seed_v, self.sumo_route,
                                                  self.v2v_equipment_percentage, self.wlan_equipment_percentage)

        if self.wlan_device and self.wlan_equipment_percentage > 0.0:
            self.wlan_manager = wlan_ap_manager.WlanAPManager(traci, self.wlan_ap_count, self.ism_layer, self.backend_server,
                                                         self.buildings_tuple, self.ap_placement, self.wlan_distance,
                                                         self.wlan_beacon_interval, self.wlan_data_rate, self.ap_coords,
                                                         self.max_number_connections, self.wlan_ap_percentage, self.seed_v)

        # size = 1000 * 1000 * 10  # 100Megabyte
        self.generated_update = False
        try:
            filename = self.backend_server.generate_update(self.update_size)  # 10 Megabyte
            self.generated_update = True
            self.update_names.append(filename)
            self.update_data[filename] = [self.traciStep, self.update_size, self.chunk_size]
        except:
            print("update not generated")

    def step(self, action: ActType) -> Tuple[ObsType, float, bool, dict]:
        """
        run sumo environment with given action = given initial seed number

        Returns:
            observation (object): agent's observation of the current environment
            reward (float) : amount of reward returned after previous action
            done (bool): whether the episode has ended, in which case further step() calls will return undefined results
            info (dict): contains auxiliary diagnostic information (helpful for debugging, and sometimes learning)

        """

        #print("step in timestep: ", self.timestep_counter)
        if self.timestep_counter > self.timesteps:
            done = True
            print("This is in the if")
            return ([int(round((float(self.state)/float(self.max_chunks)), 3)*1000.0), int(round((float(self.total_seed)/float(self.max_chunks)), 3)*1000.0), 1000, self.update_index], self.reward, done, self.info)

        remained = self.max_chunks - self.state
        seeding_number = int(action * 0.001 * self.max_chunks)
        print(seeding_number, action, "Seeding Number")
        self.state, done, chunks_loaded = self.seeding_step(action, remained)
        #print(self.traciStep)
        self.after_seed = self.state
        print(self.state)

        #print("This is in the state", done)
        #print("done", type(done))
        #print("state", self.state)
        while (self.traciStep % self.seeding_time) != 0:
            if self.timestep_counter >= self.timesteps:
                break
            self.state, done, tmp = self.simulation_step()
        self.after_time = self.state
        self.timestep_counter += 1
        #print(self.timestep_counter, self.state, done, self.timesteps)
        # Save step information
        #sparse reward
        if True:
            if self.state == self.max_chunks and not done:
                done = True
                self.reward = -0.1 * (self.timesteps - self.timestep_counter)
            elif done or self.max_chunks == self.state:
                # self.reward = (1.0 - round(((self.total_seed + self.max_chunks - self.state) * self.cost_value), 10)) \
                #              + ((1.0 - round((self.max_chunks - self.state) * self.cost_value, 10)))
                self.reward = ((1.0 - round((self.total_seed + self.max_chunks - self.state) * self.cost_value, 10)))
                costs = round(((self.total_seed + self.max_chunks - self.state) * self.cost_value), 4)
                done = True
                print("done reward", self.reward, seeding_number, action, costs, self.total_seed, self.max_chunks,
                      self.state, self.after_time - self.after_seed, self.after_time, self.after_seed)
                # + round((self.max_chunks - self.state) * self.cost_value, 4))
            else:
                # costs = round(((self.total_seed + self.max_chunks - self.state) * self.cost_value), 4)
                # self.reward = round((1-costs), 4)
                # self.reward = round(1.0 - ((self.total_seed + self.max_chunks - self.state) * self.cost_value), 10)
                costs = round(((self.total_seed + self.max_chunks - self.state) * self.cost_value), 4)
                self.reward = 0.0
                print("intermediate reward", self.reward, seeding_number, action, costs, self.total_seed,
                      self.max_chunks, self.state, self.after_time - self.after_seed, self.after_time, self.after_seed)

                costs = round(((self.total_seed + self.max_chunks - self.state) * self.cost_value), 4)
                remained = self.max_chunks - self.state

        elif False: # negative if finished too early
            if seeding_number > remained:
                self.reward = 0.0

            elif self.state == self.max_chunks and not done:
                done = True
                self.reward = -0.1 * (self.timesteps - self.timestep_counter)
            elif done:
                self.reward = (1.0 - round(((self.total_seed + self.max_chunks - self.state) * self.cost_value), 10)) \
                              + ((1.0 - round((self.max_chunks - self.state) * self.cost_value, 10)))
                costs = round(((self.total_seed + self.max_chunks - self.state) * self.cost_value), 4)
                print("done reward", self.reward, seeding_number, action, costs, self.total_seed, self.max_chunks,
                      self.state, self.after_time - self.after_seed, self.after_time, self.after_seed)
                # + round((self.max_chunks - self.state) * self.cost_value, 4))
            else:
                # costs = round(((self.total_seed + self.max_chunks - self.state) * self.cost_value), 4)
                # self.reward = round((1-costs), 4)
                self.reward = round(1.0 - ((self.total_seed + self.max_chunks - self.state) * self.cost_value), 10)
                costs = round(((self.total_seed + self.max_chunks - self.state) * self.cost_value), 4)
                print("intermediate reward", self.reward, seeding_number, action, costs, self.total_seed,
                      self.max_chunks, self.state, self.after_time - self.after_seed, self.after_time, self.after_seed)

            costs = round(((self.total_seed + self.max_chunks - self.state) * self.cost_value), 4)
            remained = self.max_chunks - self.state

        elif False: #before
            if seeding_number > remained:
                self.reward = 0.0

            elif done:
                self.reward = (1.0 - round(((self.total_seed + self.max_chunks - self.state) * self.cost_value), 10)) \
                              + (1.0 - round((self.max_chunks - self.state) * self.cost_value, 10))
                costs = round(((self.total_seed + self.max_chunks - self.state) * self.cost_value), 4)
                print("done reward", self.reward, seeding_number, action, costs, self.total_seed, self.max_chunks, self.state, self.after_time - self.after_seed, self.after_time, self.after_seed)
                # + round((self.max_chunks - self.state) * self.cost_value, 4))
            else:
                # costs = round(((self.total_seed + self.max_chunks - self.state) * self.cost_value), 4)
                # self.reward = round((1-costs), 4)
                self.reward = round(1.0 - ((self.total_seed + self.max_chunks - self.state) * self.cost_value), 10)
                costs = round(((self.total_seed + self.max_chunks - self.state) * self.cost_value), 4)
                print("intermediate reward", self.reward, seeding_number, action, costs, self.total_seed, self.max_chunks, self.state, self.after_time - self.after_seed, self.after_time, self.after_seed)

        costs = round(((self.total_seed + self.max_chunks - self.state) * self.cost_value), 4)
        remained = self.max_chunks - self.state

        

        
        # info: total seed so far, costs, bool: update done, number of chunks remained, seeding number in this step
        self.info[self.timestep_counter] = [self.total_seed, costs, done, remained, seeding_number, self.state, self.reward, action]
        self.log_episode[self.timestep_counter] = self.info[self.timestep_counter]
        
        if self.timestep_counter == self.timesteps:
            self.log_dict[self.episode] = self.log_episode    
            #print(self.log_dict[self.episode])
        #print("This is in the state", done)
        #print("done", type(done))
        #print("state", self.state)
        return ([int(round((float(self.state)/float(self.max_chunks)), 3)*1000.0), int(round((float(self.total_seed)/float(self.max_chunks)), 3)*1000.0), int(round((float(self.timestep_counter)/float(self.timesteps)), 3)*1000.0), self.update_index], self.reward, done,  self.info)

    def simulation_step(self):
        """
        traci simulation step, without any seeding
        Return: state, finished
        """

        finished = False

        try:
            traci.simulationStep()
            current_time = traci.simulation.getTime()
            self.vehicle_fleet.arrived(traci.simulation.getArrivedIDList())
            self.vehicle_fleet.departed(traci.simulation.getDepartedIDList())
            if self.v2v_device and self.v2v_equipment_percentage > 0.0:
                self.v2v_layer.simulation_step(current_time)
            if self.wlan_device and self.wlan_equipment_percentage > 0.0:
                self.connected_vehicles.extend(self.ism_layer.simulation_step(current_time))

            # end simulation run if all vehicles are gone
            finished = self.vehicle_fleet.update(current_time)
            # end simulation run if update is done
            #print("chunks: ", self.vehicle_fleet.get_update_progress_fleet(), self.max_chunks)
            if finished:
                if self.vehicle_fleet.get_update_progress_fleet() > self.max_chunks:
                    print("finished and update progress greater than update size",
                          self.vehicle_fleet.get_update_progress_fleet())
                self.time_done = current_time
            else:
                self.time_done = 0

            if not self.generated_update:
                # size = 1000 * 1000 * 10  # 100Megabyte
                filename = self.backend_server.generate_update(self.update_size)  # 10 Megabyte
                self.generated_update = True
                self.update_names.append(filename)
                self.update_data[filename] = [current_time, self.update_size, self.chunk_size]

            self.traciStep = current_time
            #if (self.traciStep % 480) == 0:
            #    print("traci time:", self.traciStep, " chunks: ",self.vehicle_fleet.get_update_progress_fleet())
        except Exception as e:
            print("Unexpected error:", sys.exc_info()[0])
            print(e)
            traceback.print_tb(sys.exc_info()[2])
        #print("sim step", self.traciStep)
        #print("finished", round(self.traciStep, 4) == round(float(self.duration_parameter), 4), self.traciStep, self.duration_parameter,round(self.traciStep, 4), round(float(self.duration_parameter), 4))
        return self.vehicle_fleet.get_update_progress_fleet(), finished or round(self.traciStep, 4) == round(float(self.duration_parameter), 4), 0

    def seeding_step(self, action: ActType, remained:int ):
        """
        traci simulation step, asks if action = seeding
        @param: action: integer from RL environment, action == 1: do not seed, action==0: seed
        @param: seeding number: integer, chunks that are seeded
        Return: state, finished
        """
        finished = False
        done = False
        seeding_number = 0
        # action == 0: no seeding
        if action == 0:
            print("In action == 0")
            return self.simulation_step()
       
        else:
            try:
                traci.simulationStep()
                current_time = traci.simulation.getTime()
                self.vehicle_fleet.arrived(traci.simulation.getArrivedIDList())
                self.vehicle_fleet.departed(traci.simulation.getDepartedIDList())
                if self.v2v_device and self.v2v_equipment_percentage > 0.0:
                    self.v2v_layer.simulation_step(current_time)
                if self.wlan_device and self.wlan_equipment_percentage > 0.0:
                    self.connected_vehicles.extend(self.ism_layer.simulation_step(current_time))

                seeding_number = int(action * 0.001 * self.max_chunks)
                
                finished, progress_list, chunks_loaded = self.vehicle_fleet.update_seeding(current_time, seeding_number)

                # print update name to check if same update is disseminated
                #print("update name 2: ", self.vehicle_fleet.get_all_vehicles()[0].getUpdate())

                # end simulation run if update is done
                # print("chunks: ", self.vehicle_fleet.get_update_progress_fleet(), self.max_chunks)
                if finished:
                    done = True
                    if self.vehicle_fleet.get_update_progress_fleet() > self.max_chunks:
                        print("finished and update progress greater than update size",
                              self.vehicle_fleet.get_update_progress_fleet())
                    self.time_done = current_time
                else:
                    self.time_done = 0

                if not self.generated_update:
                    # size = 1000 * 1000 * 10  # 100Megabyte
                    filename = self.backend_server.generate_update(self.update_size)  # 10 Megabyte
                    self.generated_update = True
                    self.update_names.append(filename)
                    self.update_data[filename] = [current_time, self.update_size, self.chunk_size]

                self.traciStep = current_time

            except Exception as e:
                print("Unexpected error:", sys.exc_info()[0])
                print(e)
                traceback.print_tb(sys.exc_info()[2])

            # update total number of seeded chunks for cost calculation
            self.total_seed += chunks_loaded
            #print("totally seeded:", self.total_seed)

            return self.vehicle_fleet.get_update_progress_fleet(), finished or round(self.traciStep, 4) == round(float(self.duration_parameter), 4), chunks_loaded

    
    def get_log_dict(self):
        return self.log_dict
    
    def get_state(self):
        return self.state


    def reset(self):
        '''
        Reset environment after one episode.

        '''
        traci.close()
        self.seed_v += 1
        random.seed(self.seed_v)
        self.timestep_counter = 0
        # reset variables
        self.update_data = {}
        self.episode += 1 
        self.log_episode = {}
        self.update_names = []
        self.time_done = 0
        self.total_seed = 0
        self.action_costs = 0
        self.total_seed = 0
        self.state = 0
        self.reward = 0

        result_data = self.vehicle_fleet.get_used_file_names()
        for element in result_data.values():
            for string in element:
                #print(self.output_abs_path + "/"+ string)
                #sys.exit()
                try:
                    os.remove(self.output_abs_path + "/" + string)
                except:
                    pass        # # delete manhatten files
        # rm_path = '/home/thummerer/chunksimulation-rl/rl_model8/validation_tests/result_files/manhattan/'
        # #for f in os.listdir(rm_path):
        #     #if not f.contains('.dat') or f.contains('.datmeta'):
        #        # os.remove(os.path.join(rm_path, f))
        #
        # filelist = glob.glob(os.path.join(rm_path, "*.dat"))
        # filelist_datmeta = glob.glob(os.path.join(rm_path,"*.datmeta"))
        # #print(filelist)
        # for f in os.listdir(rm_path):
        #     f_ = str(os.path.join(rm_path, f))
        #     #print(f_)
        #     if f_ in filelist or f_ in filelist_datmeta:
        #         pass
        #     else:
        #         #print("removing", f)
        #         try:
        #             os.remove(f)
        #         except:
        #             pass
        #shutil.rmtree(rm_path, ignore_errors=True)
        #if not os.path.exists(rm_path):        
        #    os.mkdir(rm_path)
        # create sumo environment
        pathlib.Path(self.output_abs_path).mkdir(parents=True, exist_ok=True)
        os.chdir(self.output_abs_path)
        sumo_cmd = [self.sumo_binary, "-c", self.sumo_cfg, "--seed", str(int(0)), "-S"]

        traci.start(sumo_cmd)
        self.traciStep = 0
        self.backend_server = Backend.Backend(self.chunk_size, self.initial_seeds, self.number_vehicles, self.seeding_strategy)
        self.v2v_layer = None
        self.ism_layer = None
        if self.v2v_device and self.v2v_equipment_percentage > 0.0:
            self.v2v_layer = v2vNetworkingLayer.V2VNetworkingLayer(traci, self.distance, self.data_rate,
                                                                   self.gain, self.transmission_power,
                                                                   self.pathloss, self.noisepower, self.loss_exponent,
                                                                   self.antenna_height,
                                                                   self.two_ray, self.log_distance,
                                                                   self.log_shadow, self.shadow_slope,
                                                                   self.loss_exponent2, self.sigma, self.sigma2
                                                                   )

        if self.wlan_device and self.wlan_equipment_percentage > 0.0:
            self.ism_layer = ismNetworkingLayer.ISMNetworkingLayer(traci)
        t = time.time()
        var_dump_file_name = time.strftime("%d%m%Y%H_%M_%S") + "_" + str(
            int(round(t * 1000))) + "_%i_%i_%i" % (
                                 self.additional_vehicles, self.number_vehicles, self.duration_parameter)
        for value in self.parameters:
            if type(value) is float:
                var_dump_file_name += "_%i" % (int(value * 100))
            elif type(value) is str:
                var_dump_file_name += "_" + value.replace(' ', '_')
            else:
                var_dump_file_name += "_%i" % (int(value))
        var_dump_file_name += "_%i" % self.iteration_counter

        self.vehicle_fleet = fleetManager.FleetManager(traci, self.backend_server, self.v2v_layer,
                                                       self.additional_vehicles,
                                                       self.number_vehicles,
                                                       self.duration_parameter, self.ism_layer, self.v2v_device,
                                                       self.wlan_device,
                                                       self.wlan_heartbeat_strategy, self.v2v_heartbeat_strategy,
                                                       self.heartbeat_encoding,
                                                       self.v2v_heartbeat_interval, self.v2v_distance,
                                                       self.v2v_data_rate,
                                                       var_dump_file_name, self.duration, self.wlan_distance, self.seed_v,
                                                       self.sumo_route,
                                                       self.v2v_equipment_percentage, self.wlan_equipment_percentage)

        if self.wlan_device and self.wlan_equipment_percentage > 0.0:
            self.wlan_manager = wlan_ap_manager.WlanAPManager(traci, self.wlan_ap_count, self.ism_layer,
                                                              self.backend_server,
                                                              self.buildings_tuple, self.ap_placement,
                                                              self.wlan_distance,
                                                              self.wlan_beacon_interval, self.wlan_data_rate,
                                                              self.ap_coords,
                                                              self.max_number_connections, self.wlan_ap_percentage,
                                                              self.seed_v)

        # size = 1000 * 1000 * 10  # 100Megabyte
        self.generated_update = False
        try:
            filename = self.backend_server.generate_update(self.update_size)  # 10 Megabyte
            self.generated_update = True
            self.update_names.append(filename)
            self.update_data[filename] = [self.traciStep, self.update_size, self.chunk_size]
        except:
            print("update not generated")
        
        remained = self.max_chunks - self.state
        
        seeding_number = 0
 
        costs = round(((self.total_seed + self.max_chunks - self.state) * self.cost_value),4)
        self.reward = round((1-costs),4)
        # info: total seed so far, costs, bool: update done, number of chunks remained, seeding number in this ste    p
        obs = self.state
        self.info[self.timestep_counter] = [self.total_seed, costs, self.time_done, remained, seeding_number]
        #print(self.info)
        return [0, 0, 0, self.update_index]


    def render(self):
        '''
        Implement visualization of environment, unused
        '''
        # print(self.agent_pos, observation)
        pass


    def close(self):
        self.timestep_counter = 0
        result_data = self.vehicle_fleet.get_used_file_names()
        for element in result_data.values():
            for string in element:
                #print(self.output_abs_path + "/"+ string)
                # sys.exit()
                try:
                    os.remove(self.output_abs_path + "/" + string)
                except:
                    pass
        traci.close()
        
        # save results from log_dict
        #result_file = '/home/thummerer/chunksimulation-rl/rl_model7_dqn/logs/' + 'results_' + str(random.randint(0,100)) + '.csv'
        #print(self.log_dict)
        #with open(result_file, 'w+', newline='') as r:
        #    writer = csv.writer(r)
        #    for episode in self.log_dict:
        #        writer.writerow([str(episode)])
        #        for key in self.log_dict[episode]:
        #            writer.writerow(self.log_dict[episode][key])
        
        #r.close()

 #       for update_name in self.update_names:
 #           if os.path.isfile(update_name + ".dat"):
 #               os.remove(update_name + ".dat")
                #print(os.path.isfile(update_name + ".dat")
 #           if os.path.isfile(update_name + ".datmeta"):
 #               os.remove(update_name + ".datmeta")
                #print(os.path.isfile(update_name + ".datmeta")

