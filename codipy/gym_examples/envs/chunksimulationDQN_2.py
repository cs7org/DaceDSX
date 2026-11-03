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
import shutil
ObsType = TypeVar("ObsType")
ActType = TypeVar("ActType")


class env_v2(gym.Env):
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
        # parse parameters
        self.sumo_cfg, self.sumo_binary, self.number_vehicles, self.additional_vehicles, self.update_size, self.initial_seed_number, self.v2v_distance, \
        self.duration, self.duration_parameter, self.output_abs_path, self.buildings_tuple, self.ap_placement, self.v2v_device, self.v2v_heartbeat_interval, \
        self.v2v_heartbeat_strategy, self.heartbeat_encoding, self.v2v_data_rate, self.seeding_strategy, self.parameters, self.sumo_route = parameter_parser.parse_parameter_xml(
            self.config, self.parameter_index)

        # Define variables for cost calculation
        self.chunk_size = 1411  # fixed chunk size inherited from simulation framework
        if self.update_size % self.chunk_size != 0:
            self.max_chunks = int(self.update_size / self.chunk_size)+1
        else:
            self.max_chunks = int(self.update_size / self.chunk_size)
        
        self.cost_value = 1 / self.max_chunks
        self.update_data = {}
        self.update_names = []
        self.time_done = 0
        self.total_seed = 0
        self.action_costs = 0

        # time parameters
        timelimit = 480.0
        self.timesteps = 8
        self.timestep_counter = 0
        self.seeding_time = int(timelimit / self.timesteps)

        # Define action and observation space (must be gym spaces objects)
        # Actions we can take:
        # 0, 5, 10, 50, 100 % seed of left update size
        self.action_size = 5
        self.action_space = spaces.Discrete(self.action_size)
        # Observations: All environment's data to be observed by agent
        # seeds at the end of download time
        self.observation_space = spaces.Discrete(self.max_chunks+1)
        # State: update_progress
        self.state = self.initial_seed_number
        self.seed_size = 0.05
        
        self.reward = 0
        
        # create log dict
        self.log_dict = {}
        self.log_episode = {}

        # close traci simulations
        try:
            traci.close()
        except:
            pass

        # create sumo environment
        pathlib.Path(self.output_abs_path).mkdir(parents=True, exist_ok=True)
        os.chdir(self.output_abs_path)
        sumo_cmd = [self.sumo_binary, "-c", self.sumo_cfg, "--seed", str(int(self.initial_seed_number)), "-S"]

        traci.start(sumo_cmd)
        self.traciStep = 0
        self.backend_server = Backend.Backend(self.chunk_size, self.number_vehicles, self.seeding_strategy)
        self.v2v_layer = v2vNetworkingLayer.V2VNetworkingLayer(traci)
        t = time.time()

        self.var_dump_file_name = time.strftime("%d%m%Y%H_%M_%S") + "_" + str(
             int(round(t * 1000))) + "_%i_%i_%i" % (
                                       self.additional_vehicles, self.number_vehicles, self.duration_parameter)
        for value in self.parameters:
            if type(value) is float:
                self.var_dump_file_name += "_%i" % (int(value * 100))
            elif type(value) is str:
                self.var_dump_file_name += "_" + value.replace(' ', '_')
            else:
                self.var_dump_file_name += "_%i" % (int(value))
        self.var_dump_file_name += "_%i" % self.iteration_counter

        # initialize fleet manager
        self.vehicle_fleet = fleetManager.FleetManager(traci, self.backend_server, self.v2v_layer,
                                                       self.additional_vehicles,
                                                       self.number_vehicles, self.duration_parameter,
                                                       self.v2v_device, self.v2v_heartbeat_strategy,
                                                       self.heartbeat_encoding,
                                                       self.v2v_heartbeat_interval, self.v2v_distance,
                                                       self.v2v_data_rate,
                                                       self.var_dump_file_name, self.duration,
                                                       sumo_route=self.sumo_route)
        # size = 1000 * 1000 * 10  # 100Megabyte
        self.generated_update = False
        try:
            filename = self.backend_server.generate_update(self.update_size)  # 10 Megabyte
            self.generated_update = True
            self.update_names.append(filename)
            self.update_data[filename] = [self.traciStep, self.update_size, self.chunk_size]
        except:
            print("update not generated")

    def step(self, action: ActType) -> Tuple[ObsType, float, bool, bool, dict]:
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
            return [self.state, self.reward, done, self.info]

        remained = self.max_chunks - self.state
        self.state, done = self.seeding_step(action, remained)

        
        while (self.traciStep % self.seeding_time) != 0:
            if self.timestep_counter >= self.timesteps:
                break
            self.state, done = self.simulation_step()

        self.timestep_counter += 1

        # Save step information
        #print("state after timestep:", self.state)
        costs = round(((self.total_seed + self.max_chunks - self.state) * self.cost_value),4)
        self.reward = round((1-costs),4)
        #print("costs : ",costs)
        remained = self.max_chunks - self.state
        seeding_number = 0
        if action == 1:
            seeding_number = int(remained*0.05)
        elif action == 2:
            seeding_number = int(remained*0.1)
        elif action == 3:
            seeding_number = int(remained*0.5)
        elif action == 4:
            seeding_number = remained
        # info: total seed so far, costs, bool: update done, number of chunks remained, seeding number in this step
        self.info[self.timestep_counter] = [self.total_seed, costs, done, remained, seeding_number, self.state, self.reward,action]
        self.log_episode[self.timestep_counter] = self.info[self.timestep_counter]
        
        if self.timestep_counter == self.timesteps:
            self.log_dict[self.episode] = self.log_episode    
            #print(self.log_dict[self.episode])
        
        return self.state, self.reward, done,  self.info

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
            self.v2v_layer.simulation_step(current_time)

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

        return self.vehicle_fleet.get_update_progress_fleet(), finished

    def seeding_step(self, action: ActType, remained:int ):
        """
        traci simulation step, asks if action = seeding
        @param: action: integer from RL environment, action == 1: do not seed, action==0: seed
        @param: seeding number: integer, chunks that are seeded
        Return: state, finished
        """
        finished = False
        seeding_number = 0
        # action == 0: no seeding
        if action == 0:
            #print("normal simulation step")
            return self.simulation_step()
       
       # actions 1,2,3,4 seeding
        else:
            #print("seeding step: ", seeding_number)
            try:
                traci.simulationStep()
                current_time = traci.simulation.getTime()
                self.vehicle_fleet.arrived(traci.simulation.getArrivedIDList())
                self.vehicle_fleet.departed(traci.simulation.getDepartedIDList())
                self.v2v_layer.simulation_step(current_time)

                # print update name to check if same update is disseminated
                #print("update name 1: ", self.vehicle_fleet.get_all_vehicles()[0].getUpdate())

                # end simulation run if all vehicles are gone
                if action == 1:
                    seeding_number = int(remained*0.1)
                elif action == 2:
                    seeding_number = int(remained*0.05)
                elif action == 3:
                    seeding_number = int(remained*0.5)
                elif action == 4:
                    seeding_number = int(remained)
                
                finished = self.vehicle_fleet.update_seeding(current_time, seeding_number)
                # print update name to check if same update is disseminated
                #print("update name 2: ", self.vehicle_fleet.get_all_vehicles()[0].getUpdate())

                # end simulation run if update is done
                # print("chunks: ", self.vehicle_fleet.get_update_progress_fleet(), self.max_chunks)
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

            except Exception as e:
                print("Unexpected error:", sys.exc_info()[0])
                print(e)
                traceback.print_tb(sys.exc_info()[2])

            # update total number of seeded chunks for cost calculation
            self.total_seed += seeding_number
            #print("totally seeded:", self.total_seed)

            return self.vehicle_fleet.get_update_progress_fleet(), finished

    
    def get_log_dict(self):
        return self.log_dict
    
    def get_state(self):
        return self.state


    def reset(self):
        '''
        Reset environment after one episode.

        '''
        traci.close()
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
        
        # delete manhatten files
        rm_path = '/home/thummerer/chunksimulation-rl/rl_model8/validation_tests/result_files/manhattan/'
        #for f in os.listdir(rm_path):
            #if not f.contains('.dat') or f.contains('.datmeta'):
               # os.remove(os.path.join(rm_path, f))

        filelist = glob.glob(os.path.join(rm_path, "*.dat"))
        filelist_datmeta = glob.glob(os.path.join(rm_path,"*.datmeta"))
        #print(filelist)
        for f in os.listdir(rm_path):
            f_ = str(os.path.join(rm_path, f))
            #print(f_)
            if f_ in filelist or f_ in filelist_datmeta:
                pass
            else:
                #print("removing", f)
                try:
                    os.remove(f)
                except:
                    pass
        #shutil.rmtree(rm_path, ignore_errors=True)
        #if not os.path.exists(rm_path):        
        #    os.mkdir(rm_path)
        # create sumo environment
        pathlib.Path(self.output_abs_path).mkdir(parents=True, exist_ok=True)
        os.chdir(self.output_abs_path)
        sumo_cmd = [self.sumo_binary, "-c", self.sumo_cfg, "--seed", str(int(self.initial_seed_number)), "-S"]

        traci.start(sumo_cmd)
        self.traciStep = 0
        self.backend_server = Backend.Backend(self.chunk_size, self.number_vehicles, self.seeding_strategy)
        self.v2v_layer = v2vNetworkingLayer.V2VNetworkingLayer(traci)
        t = time.time()
        self.var_dump_file_name = time.strftime("%d%m%Y%H_%M_%S") + "_" + str(
            int(round(t * 1000))) + "_%i_%i_%i" % (
                                      self.additional_vehicles, self.number_vehicles, self.duration_parameter)
        for value in self.parameters:
            if type(value) is float:
                self.var_dump_file_name += "_%i" % (int(value * 100))
            elif type(value) is str:
                self.var_dump_file_name += "_" + value.replace(' ', '_')
            else:
                self.var_dump_file_name += "_%i" % (int(value))
        self.var_dump_file_name += "_%i" % self.iteration_counter

        # initialize fleet manager
        self.vehicle_fleet = fleetManager.FleetManager(traci, self.backend_server, self.v2v_layer,
                                                       self.additional_vehicles,
                                                       self.number_vehicles, self.duration_parameter,
                                                       self.v2v_device, self.v2v_heartbeat_strategy,
                                                       self.heartbeat_encoding,
                                                       self.v2v_heartbeat_interval, self.v2v_distance,
                                                       self.v2v_data_rate,
                                                       self.var_dump_file_name, self.duration,
                                                       sumo_route=self.sumo_route)
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
        return obs


    def render(self):
        '''
        Implement visualization of environment, unused
        '''
        # print(self.agent_pos, observation)
        pass


    def close(self):
        self.timestep_counter = 0
        
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

