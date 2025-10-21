import os
import pathlib
import random
import sys
from typing import Optional, Union, Tuple

from pathlib import Path
import pandas as pd
from gym.core import ObsType, ActType
from gym.spaces import Discrete
import numpy as np
import functools
from pettingzoo import AECEnv
from pettingzoo.utils import agent_selector
from pettingzoo.utils import wrappers
from gym.utils import EzPickle, seeding
from pettingzoo.utils.agent_selector import agent_selector
from pettingzoo.utils.conversions import parallel_wrapper_fn
import gym
from gym.envs.registration import EnvSpec
import os
import sys
import time

from samba.dcerpc.security import acl

import Backend as Backend
import FleetManager as fleetManager
import V2VNetworkingLayer as v2vNetworkingLayer
import ISMNetworkingLayer as ismNetworkingLayer
import csv
import pathlib
import WlanAPManager as wlan_ap_manager
import traceback
import random
import getopt
import parameter_parser
from typing import List

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("please declare environment variable 'SUMO_HOME'")
import traci
import traci.constants as tc



def env(**kwargs):
    '''
    The env function often wraps the environment in wrappers by default.
    You can find full documentation for these methods
    elsewhere in the developer documentation.
    '''
    env = ChunksimulationEnvironmentPettingZoo(**kwargs)
    # This wrapper is only for environments which print results to the terminal
    env = wrappers.CaptureStdoutWrapper(env)
    # this wrapper helps error handling for discrete action spaces
    env = wrappers.AssertOutOfBoundsWrapper(env)
    # Provides a wide vareity of helpful user errors
    # Strongly recommended
    env = wrappers.OrderEnforcingWrapper(env)
    return env

parallel_env = parallel_wrapper_fn(env)



class ChunksimulationEnvironment(gym.Env):
    CONNECTION_LABEL = 0  # For traci multi-client support
    def _parse_options(argv: List[str]) -> (
    str, int, int, float):  # parse multiple logfiles, put plots, calculated values and traces in new directory
        """
        Parse command line options.
        @param argv: List of command line arguments
        @return: index in parameter variation, iteration
        """
        usage = 'usage: simulation_run.py [-h | --help] [-c | --config<str>] [-p | --parameter_index<number>] [-i | --iteration=<number>] [-s | --seed=<number>]' + '\n' + \
                'Parameter runs'
        parameter_index = None
        iteration = None
        seed = 0
        config = None

        try:
            if len(argv) == 0:
                raise getopt.GetoptError("No input arguments")
            opts, args = getopt.getopt(argv, "hc:p:i:s:",
                                       ["help", "config=", "parameter_index=", "iteration=", "seed="])
            if len(opts) == 0:
                raise getopt.GetoptError("No option specified")
            for opt, arg in opts:
                if opt in ("-h", "--help"):
                    print(usage)
                    sys.exit()
                elif opt in ("-p", "--parameter_index"):
                    parameter_index = arg
                elif opt in ("-i", "--iteration"):
                    iteration = arg
                elif opt in ("-s", "--seed"):
                    seed = arg
                elif opt in ("-c", "--config"):
                    config = arg

        except getopt.GetoptError:
            print(usage)
            sys.exit(2)
        if parameter_index is None or iteration is None or config is None:
            print(usage)
            sys.exit(2)
        config = os.path.abspath(config)
        return str(config), int(parameter_index), int(iteration), float(seed)


    def __init__(self, config: str, parameter_index: int, iteration_counter: int, seed: float, out_csv_name):
        self.finished = False
        random.seed(seed)
        self.seed = seed
        self.iteration_counter = iteration_counter
        self.sumo_cfg, self.sumo_binary, self.number_vehicles, self.additional_vehicles, self.update_size, self.initial_seeds, self.v2v_distance, self.duration, \
        self.duration_parameter, self.output_abs_path, self.buildings_tuple, self.ap_placement, self.v2v_device, self.wlan_device, self.wlan_distance, self.wlan_beacon_interval, self.v2v_heartbeat_interval, self.wlan_ap_count, self.wlan_heartbeat_strategy, self.v2v_heartbeat_strategy, self.heartbeat_encoding, self.v2v_data_rate, self.wlan_data_rate, self.seeding_strategy, self.parameters = parameter_parser.parse_parameter_xml(
            config, parameter_index)

        pathlib.Path(self.output_abs_path).mkdir(parents=True, exist_ok=True)
        os.chdir(self.output_abs_path)
        self.label = str(ChunksimulationEnvironment.CONNECTION_LABEL)
        ChunksimulationEnvironment.CONNECTION_LABEL += 1
        self.reward_range = (-70872.0, 0.0) #(-float('inf'), float('inf'))
        self.metadata = {}
        self.spec = EnvSpec('CHSIM-v0')
        self.run = 0
        self.metrics = []
        self.out_csv_name = out_csv_name
        self.veh_ids = []
        for i in range(self.number_vehicles):
            self.veh_ids.append("vehicle" + str(i))
        self._start_simulation()
        self.__was_init = True
        self._init_vehicles()
        #self.vehicles = {}{veh: None for veh in self.veh_ids}
        self.observations = {veh: None for veh in self.veh_ids}
        self.rewards = {veh: None for veh in self.veh_ids}

    def _init_vehicles(self):
        all_vehicles = self.vehicle_fleet.get_all_vehicles()
        self.vehicles = {}
        for veh in all_vehicles:
            # print(veh.get_veh_id(), type(veh.get_veh_id()))
            self.vehicles[str(veh.get_veh_id())] = veh

    def _start_simulation(self):
        sumo_cmd = [self.sumo_binary, "-c", self.sumo_cfg, "--seed", str(int(self.seed)), "-S"]
        traci.start(sumo_cmd)
        #self.step = 0
        # chunk_size = 1411
        self.backend_server = Backend.Backend(1411, self.initial_seeds, self.number_vehicles,
                                         self.seeding_strategy)
        self.v2v_layer = None
        self.ism_layer = None
        if self.v2v_device:
            self.v2v_layer = v2vNetworkingLayer.V2VNetworkingLayer(traci)
        if self.wlan_device:
            self.ism_layer = ismNetworkingLayer.ISMNetworkingLayer(traci)
        t = time.time()
        self.var_dump_file_name = time.strftime("%d%m%Y%H_%M_%S") + "_" + str(
            int(round(t * 1000))) + "_%i_%i_%i" % (
                                 self.additional_vehicles, self.number_vehicles, self.duration_parameter)  # , initial_seeds,
        # v2v_distance, iteration_counter)
        for value in self.parameters:
            if type(value) is float:
                self.var_dump_file_name += "_%i" % (int(value * 100))
            elif type(value) is str:
                self.var_dump_file_name += "_" + value.replace(' ', '_')
            else:
                self.var_dump_file_name += "_%i" % (int(value))
        self.var_dump_file_name += "_%i" % self.iteration_counter

        self.vehicle_fleet = fleetManager.FleetManager(traci, self.backend_server, self.v2v_layer, self.additional_vehicles,
                                                  self.number_vehicles,
                                                  self.duration_parameter, self.ism_layer, self.v2v_device, self.wlan_device,
                                                  self.wlan_heartbeat_strategy, self.v2v_heartbeat_strategy, self.heartbeat_encoding,
                                                  self.v2v_heartbeat_interval, self.v2v_distance, self.v2v_data_rate,
                                                  self.var_dump_file_name, self.duration, self.wlan_distance, self.seed)
        if self.wlan_device:
            self.wlan_manager = wlan_ap_manager.WlanAPManager(traci, self.wlan_ap_count, self.ism_layer, self.backend_server,
                                                         self.buildings_tuple, self.ap_placement, self.wlan_distance,
                                                         self.wlan_beacon_interval, self.wlan_data_rate)
        self.generate_update_one = False
        self.generate_update_two = False
        self.finished = False
        self.update_data = {}
        self.update_names = []
        self.simulation_step_counter = 0

    def _simulation_step(self):
        if self.duration and self.simulation_step_counter < self.duration_parameter * 10:
            traci.simulationStep()
            current_time = traci.simulation.getTime()
            self.vehicle_fleet.arrived(traci.simulation.getArrivedIDList())
            self.vehicle_fleet.departed(traci.simulation.getDepartedIDList())
            if self.v2v_device:
                self.v2v_layer.simulation_step(current_time)
            if self.wlan_device:
                self.ism_layer.simulation_step(current_time)
            finished = self.vehicle_fleet.update(current_time)

            if not self.generate_update_two:  # 6000
                # size = 1000 * 1000 * 100  # 50 Megabyte
                filename = self.backend_server.generate_update(self.update_size)  # 50 Megabyte
                self.generate_update_two = True
                self.update_names.append(filename)
                self.update_data[filename] = [current_time, self.update_size, 1411]
            # h.heap()
            self.simulation_step_counter += 1
            return False
        else:
            return True

    def step(self, action: ActType): # -> Tuple[ObsType, float, bool, dict]:
        #if action is None:
        #    self._simulation_step()
        #else:
            #self._apply_actions(action)
        #    self._simulation_step()
        self.finished = self._simulation_step()
        #if self.finished:

        observations = self._compute_observations()
        rewards = self._compute_rewards()
        dones = self._compute_dones()
        self._compute_info()
        return observations, rewards, dones, {}

    def _apply_actions(self, actions):
        """
        Set the next green phase for the traffic signals
        :param actions: If single-agent, actions is an int between 0 and self.num_green_phases (next green phase)
                        If multiagent, actions is a dict {ts_id : greenPhase}
        """
        #for veh, action in actions.items():
        #print()
        #print("Blub", actions)
        for key in actions:
            self.vehicles[key].apply_action(actions[key])
        #self.vehicles[actions].apply_action(action)
            #if self.traffic_signals[ts].time_to_act:
            #    self.traffic_signals[ts].set_next_phase(action)

    #def close(self):
    #    traci.close()

    def reset(self, *, seed: Optional[int] = None, return_info: bool = False, options: Optional[dict] = None): #-> Union[ObsType, tuple[ObsType, dict]]:
        #self._start_simulation()
        #print(self._compute_observations())
        if not self.__was_init:
            traci.close()
            self._start_simulation()
            self._init_vehicles()
        self.__was_init = False
        return self._compute_observations()

    def render(self, mode="human"):
        pass

    def _compute_step_info(self):
        return {
            'step_time': self.simulation_step_counter,
            'reward': self.vehicles[self.veh_ids[0]].compute_reward()
            #'total_stopped': sum(self.vehicles[veh].get_total_queued() for veh in self.veh_ids),
            #'total_wait_time': sum(sum(self.vehicles[ts].get_waiting_time_per_lane()) for ts in self.veh_ids)
        }

    def _compute_observations(self):
        #print(self.observations)
        self.observations.update({veh: self.vehicles[veh].compute_observation() for veh in self.veh_ids})# if self.traffic_signals[ts].time_to_act})
        #print(self.observations)
        return {veh: self.observations[veh] for veh in self.observations.keys()} # if self.traffic_signals[ts].time_to_act}

    def _compute_rewards(self):
        self.rewards.update({veh: self.vehicles[veh].compute_reward() for veh in self.veh_ids}) #if self.traffic_signals[veh].time_to_act})
        return {veh: self.rewards[veh] for veh in self.rewards.keys()} # if self.traffic_signals[ts].time_to_act}

    def _compute_dones(self, agent = None):
        #vehicle wird fertig, ohne einen step, weßhalb last fehltschlägt
        done = {self.vehicles[veh].get_veh_id(): self.vehicles[veh].update_done(agent) for veh in self.vehicles}
        done['__all__'] = self.finished
        return done

    def _compute_info(self):
        info = self._compute_step_info()
        self.metrics.append(info)

    def observation_spaces(self, veh_id):
        return self.vehicles[veh_id].observation_space

    def action_spaces(self, veh_id):
        return self.vehicles[veh_id].action_space

    def next_state(self, agent):
        return self.vehicles[agent].compute_observation() + 1

    def save_csv(self, out_csv_name, run):
        if out_csv_name is not None:
            df = pd.DataFrame(self.metrics)
            Path(Path(out_csv_name).parent).mkdir(parents=True, exist_ok=True)
            df.to_csv(out_csv_name + '_conn{}_run{}'.format(self.label, run) + '.csv', index=False)


class ChunksimulationEnvironmentPettingZoo(AECEnv, EzPickle):
    '''
    The metadata holds environment constants. From gym, we inherit the "render.modes",
    metadata which specifies which modes can be put into the render() method.
    At least human mode should be supported.
    The "name" metadata allows the environment to be pretty printed.
    '''
    metadata = {'render_modes': ['human'], "name": "rps_v2"}

    def __init__(self, **kwargs):
        '''
        The init method takes in environment arguments and
         should define the following attributes:
        - possible_agents
        - action_spaces
        - observation_spaces

        These attributes should not be changed after initialization.
        '''
        EzPickle.__init__(self, **kwargs)
        self._kwargs = kwargs
        self.env = ChunksimulationEnvironment(**self._kwargs)

        self.agents = self.env.veh_ids
        self.possible_agents = self.env.veh_ids
        self._agent_selector = agent_selector(self.agents)
        self.agent_selection = self._agent_selector.reset()
        # spaces
        self.action_spaces = {a: self.env.action_spaces(a) for a in self.agents}
        self.observation_spaces = {a: self.env.observation_spaces(a) for a in self.agents}

        # dicts
        self.rewards = {a: 0 for a in self.agents}
        self.dones = {a: False for a in self.agents}
        self.infos = {a: {} for a in self.agents}

    # this cache ensures that same space object is returned for the same agent
    # allows action space seeding to work as expected
    @functools.lru_cache(maxsize=None)
    def observation_space(self, agent):
        # Gym spaces are defined and documented here: https://gym.openai.com/docs/#spaces
        return self.observation_spaces[agent]

    @functools.lru_cache(maxsize=None)
    def action_space(self, agent):
        return self.action_spaces[agent]

    def step(self, action):
        '''
        step(action) takes in an action for the current agent (specified by
        agent_selection) and needs to update
        - rewards
        - _cumulative_rewards (accumulating the rewards)
        - dones
        - infos
        - agent_selection (to the next agent)
        And any internal state used by observe() or render()
        '''
        if self.dones[self.agent_selection]:
            return self._was_done_step(action)
        agent = self.agent_selection
        if not self.action_spaces[agent].contains(action):
            raise Exception('Action for agent {} must be in Discrete({}).'
                            'It is currently {}'.format(agent, self.action_spaces[agent].n, action))

        self.env._apply_actions({agent: action})

        if self._agent_selector.is_last():
            #print("pz step action", action, agent)
            self.env.step(action)
            self.env._compute_observations()
            self.rewards = self.env._compute_rewards()
            self.env._compute_info()
        else:
            self._clear_rewards()
        #self.dones[agent] = self.env._compute_dones()[]
        #self.dones = self.env._compute_dones(agent)
        done = self.env._compute_dones()['__all__']
        self.dones = {a: done for a in self.agents}

        self.agent_selection = self._agent_selector.next()
        self._cumulative_rewards[agent] = 0
        self._accumulate_rewards()

    def state(self):
        raise NotImplementedError('Method state() currently not implemented.')

    def reset(self):
        '''
        Reset needs to initialize the following attributes
        - agents
        - rewards
        - _cumulative_rewards
        - dones
        - infos
        - agent_selection
        And must set up the environment so that render(), step(), and observe()
        can be called without issues.

        Here it sets up the state dictionary which is used by step() and the observations dictionary which is used by step() and observe()
        '''
        self.env.reset()
        self.agents = self.possible_agents[:]
        self.agent_selection = self._agent_selector.reset()
        self.rewards = {agent: 0 for agent in self.agents}
        self._cumulative_rewards = {agent: 0 for agent in self.agents}
        self.dones = {agent: False for agent in self.agents}
        self.infos = {agent: {} for agent in self.agents}



    def observe(self, agent):
        '''
        Observe should return the observation of the specified agent. This function
        should return a sane observation (though not necessarily the most up to date possible)
        at any time after reset() is called.
        '''
        obs = self.env.observations[agent]
        return obs

    def close(self):
        '''
        Close should release any graphical displays, subprocesses, network connections
        or any other environment data which should not be kept around after the
        user is no longer using the environment.
        '''
        self.env.close()

    def render(self, mode='human'):
        '''
        Renders the environment. In human mode, it can print to terminal, open
        up a graphical window, or open up some other display that a human can see and understand.
        '''
        return self.env.render(mode)

