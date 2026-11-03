import os
import gym
import numpy as np
import matplotlib as plt
import random
import gym_examples
import numpy as np
import csv
import time
import sys
import getopt
from stable_baselines3 import A2C
from stable_baselines3.common.vec_env import SubprocVecEnv, DummyVecEnv
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.results_plotter import load_results, ts2xy
from typing import List, TypeVar, Tuple
ObsType = TypeVar("ObsType")
ActType = TypeVar("ActType")

class SaveOnBestTrainingRewardCallback(BaseCallback):
    """
    Callback for saving a model (the check is done every ''check_freq'' steps)
    based on training reward

    @param check_freq (int)
    @param log_dir It must contain the file created by the ''Monitor'' wrapper
    @param verbose (int)
    """
    def __init__(self, check_freq: int, log_dir: str, verbose=1):
        super(SaveOnBestTrainingRewardCallback, self).__init__(verbose)
        self.check_freq = check_freq
        self.log_dir = log_dir
        self.save_path = os.path.join(log_dir, 'best_model')
        self.best_mean_reward = -np.inf
        self.log_dict = {}
        

    def _init_callback(self) -> None:
        # Create folder if needed
        if self.save_path is not None:
            os.makedirs(self.save_path, exist_ok=True)
    
    def _on_training_end(self):
        self.log_dict = self.training_env.env_method('get_log_dict')
        
    def get_log(self):
        return self.log_dict

    def _on_step(self) -> bool:
        #self.log_dict[self.n_calls] = self.training_env.env_method('get_state')
        #print(self.log_dict)
        if self.n_calls % self.check_freq == 0:
            # get infos from environment
            #target_remotes = self.training_env._get_target_remotes(None)
            #for remote in target_remotes:
            #    remote.send(('get_state', ()))
            #for remote in target_remotes:
            #    remote.recv()
            # Retrieve training reward
            x,y = ts2xy(load_results(self.log_dir), 'timesteps')
            if len(x) > 0:
                mean_reward = np.mean(y[-100:])
                if self.verbose > 0:
                    print("Num timesteps: {}".format(self.num_timesteps))
                    print("Best mean reward: {:.2f} - Last mean reward per episode: {:.2f}".format(self.best_mean_reward, mean_reward))

                if mean_reward > self.best_mean_reward:
                    self.best_mean_reward = mean_reward
                    # Example for saving best model
                    if self.verbose > 0:
                        print("Saving new best model to {}".format(self.save_path))
                    self.model.save(self.save_path)
                    

        return True


def evaluate(model, env, episodes=50):
    """
    Evaluation of current policy without exploration (deterministic actions)
    If the current policy is better than the best policy we overwrite the best policy
    Saves evaluation results in customized csv logfiles
    @param model: (BaseRLModel) object - the DQN Agent
    @param steps: (int) number of episodes to evaluate
    @return: (float) Man reward
    """

    print ("############## Evaluation ##############")
    start = time.time()
    episode_rewards = []
    s_ = env.reset()
    ex_times_episodes = []

    for i in range(episodes - 1):
        episode_reward = 0
        step_infos = []
        start_episode = time.time()
        while True:
            done = False
            a, _ = model.predict(s_, deterministic=True)
            # q-learning step: successor state, reward, bool: update done, info:
            s_, r, done, info = env.step(a)         # one rl step is timelimit/timesteps  traci steps
            episode_reward += r
            if done.all():    # simulation done
                break

        ex_times_episodes.append(time.time() - start_episode)
        # initial seed, reward, costs, execution time
        episode_rewards.append([i for i in episode_reward]) 

        i += 1
        s_ = env.reset()

    # calculate mean reward
    mean_reward = round(np.mean(episode_rewards), 4)
    print("Mean reward:", mean_reward, "Num episodes:", episodes )
    #eval_rewards.append(mean_reward)

    # log information to csv file
    ex_time = time.time() - start
    ex_times_episodes.append(ex_time)
    #os.chdir(self.path + '/dqn_results/')
    #result_file_name = 'results_rl_%i.csv' % (self.total_episodes)
    #with open(result_file_name, 'w+', newline='') as r_file:
    #    writer = csv.writer(r_file)
    #    for key in log_dict:
    #        # step infos,total_reward, ex_time
    #        writer.writerow((log_dict[key][0], log_dict[key][1],log_dict[key][2], log_dict[key][3]))

    #ex_time_file_name = "execution_times/execution_time_rl_%i.csv"
    #with open(ex_time_file_name, 'w+', newline='') as r_file:
    #    writer = csv.writer(r_file)
    #    writer.writerow(ex_times_episodes)

    # go back to initial working directory
    #os.chdir(path)

    return mean_reward
    #return



if __name__ == "__main__":
    """
    Actor Critic Learning, using stablebaselines3 A2C algorithm
    """
    
    #create VecEnv for multiprocessing with SubprocVecEnv
    n_envs = 24
    monitor_dir = os.getcwd() + '/monitoring_envs/'
    #env_id = Env.chunksimulation_env(config='config_seeding_strategy_update2.xml', parameter_index=0,iteration_counter=0,out_csv_name=None)
    #env = Env.chunksimulation_env(config=config, parameter_index=0,iteration_counter=0,out_csv_name=None)
    #print("type env", type(env_id))
    env = make_vec_env(env_id='gym_examples/Chunksimulation-A2C-v2', n_envs=n_envs, monitor_dir=monitor_dir, vec_env_cls=SubprocVecEnv, seed=0)

    # variables for callback function
    episodes = 800
    checks = 240
    #learning_rates = [i for i in np.arange(0,0.1,0.01)]

    # callback function
    #eval_callback = EvalCallback(env, best_model_save_path='./logs/', log_path='./logs/', eval_freq=100, deterministic=True, render=False, verbose=1)
    new_callback = SaveOnBestTrainingRewardCallback(check_freq= checks, log_dir=monitor_dir)

    # exploration parameters
    max_epsilon = 1.0  # exploration probability at start
    min_epsilon = 0.01  # minimum exploration probability
    #decay_rate = 0.0005  # exponential decay rate for exploration prob
    timesteps = 60   # Horizon H = simulation steps per episode

    # deep learning parameters
    iters = episodes * timesteps  # number of simulation timesteps during training

    # define NN structure
    #hidden_layer_size = 256
    #policy_kwargs = dict([self.hidden_layer_size, self.hidden_layer_size])
    #layers = 2  # number of layers in NN
    policy_kwargs_v = dict( #activation_fn=th.nn.ReLU, 
    net_arch=[32, 32])
    # load tensorboard log
    logdir = "A2C_60_min"
    if not os.path.exists(logdir):
        os.makedirs(logdir)
    #tensorboard_log = "./A2C/"
    #tensorboard_log = None

    model = A2C("MlpPolicy", env, learning_rate=0.0007, n_steps=60, gamma=0.99, gae_lambda=1.0, ent_coef=0.0,
                vf_coef=0.5, max_grad_norm=0.5, rms_prop_eps=1e-05, use_rms_prop=True, use_sde=False,
                sde_sample_freq=-1, normalize_advantage=False, tensorboard_log=logdir, policy_kwargs=None,
                verbose=1, seed=1, device='auto', _init_setup_model=True)

    # first: evaluate model before learning
    #print("######################## EVALUATION before learning: ", evaluate(model, env, episodes=10))

    # learn
    start = time.time()
    for i in range(1, 501):
        model.learn(total_timesteps=100, log_interval=1, callback=new_callback, tb_log_name="A2C", reset_num_timesteps=False)
        if i%50 == 0:
            model.save("a2c_env_2_" +str(i))
    model.save("a2c_env_2")
    elapsed_time = time.time() - start

    print("######### Model created and trained #########")
    print("Training time:", elapsed_time)
    
    # create log files (.csv), get log_dict from GymEnvironment
    log_dict = new_callback.get_log()
    result_file = os.getcwd() + '/logs/' + 'log_dict_' + str(episodes) + '.csv'
    with open(result_file, 'w+', newline='') as r:
        writer = csv.writer(r)
        for i in range(len(log_dict)):
            for episode in log_dict[i]:
                    writer.writerow([str(episode)])
                    for timestep in log_dict[i][episode]:
                        writer.writerow(log_dict[i][episode][timestep])

    #print("######################## EVALUATION after learning: ", evaluate(model, env, episodes=10))
    env.close()


