import os
import gym
import numpy as np
import matplotlib.pyplot as plt
import random

from stable_baselines3.common.evaluation import evaluate_policy

import gym_examples
import numpy as np
import csv
import time
import sys
import getopt
from stable_baselines3 import PPO, A2C
from stable_baselines3.common.vec_env import SubprocVecEnv, DummyVecEnv
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.results_plotter import load_results, ts2xy
from typing import List, TypeVar, Tuple
ObsType = TypeVar("ObsType")
ActType = TypeVar("ActType")

class SaveOnBestTrainingRewardCallback(BaseCallback):
    '''
    Callback for saving a model (the check is done every ''check_freq'' steps)
    based on training reward

    :param check_freq: (int)
    :param log_dir: It must contain the file created by the ''Monitor'' wrapper
    :param verbose: (int)
    '''
    def __init__(self, check_freq: int, log_dir: str, verbose=1):
        super(SaveOnBestTrainingRewardCallback, self).__init__(verbose)
        self.check_freq = check_freq
        self.log_dir = log_dir
        self.save_path = os.path.join(log_dir, 'best_model_ppo')
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
    obs = env.reset()
    ex_times_episodes = []
    episodes_actions = []
    # for i in range(20):
    #     print(_states)
    #     action, _states = model.predict(_states, deterministic=False)
    #     #s_ = [[i, i, i, 0, 0, 0]]
    #     print(action, _states)
    # sys.exit()
    for i in range(episodes):
        #model.set_random_seed(10)
        episode_reward = 0
        step_infos = []
        start_episode = time.time()
        actions = []
        while True:
            done = False
            #obs = [[954,  27, 667,   0,  27,   0]]
            action, _states = model.predict(obs, deterministic=False)
            print(_states, obs)
            # q-learning step: successor state, reward, bool: update done, info:
            obs, r, done, info = env.step(action)         # one rl step is timelimit/timesteps  traci steps
            print("action", action, "reward", r, "done", done, "states", obs)
            actions.append(action[0])
            episode_reward += r
            if done.all():    # simulation done
                break

        ex_times_episodes.append(time.time() - start_episode)
        # initial seed, reward, costs, execution time
        episode_rewards.append([it for it in episode_reward])
        s = "Episode: " + str(i) + "\n"
        for l in actions:
            s += str(l) + ", "
        s = s[:-2] + "\nReward: " + str(episode_reward[0]) + "\n"

        episodes_actions.append(s)
        print(s)
        i += 1
        s_ = env.reset()

    # calculate mean reward
    mean_reward = round(np.mean(episode_rewards), 4)
    print("Mean reward:", mean_reward, "Num episodes:", episodes )
    for eps in episodes_actions:
        print(eps)
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
    Actor Critic Learning, using stablebaselines3 PPO algorithm
    """
    
    #create VecEnv for multiprocessing with SubprocVecEnv
    n_envs = 1
    monitor_dir = os.getcwd() + '/monitoring_envs_ppo/'
    #env_id = Env.chunksimulation_env(config='config_seeding_strategy_update2.xml', parameter_index=0,iteration_counter=0,out_csv_name=None)
    #env = Env.chunksimulation_env(config=config, parameter_index=0,iteration_counter=0,out_csv_name=None)
    #print("type env", type(env_id))
    env = make_vec_env(env_id='gym_examples/Chunksimulation-A2C-v2', n_envs=n_envs, monitor_dir=monitor_dir, vec_env_cls = SubprocVecEnv) #, vec_env_cls=SubprocVecEnv, seed=0)

    # variables for callback function
    episodes = 800
    checks = 160
    #learning_rates = [i for i in np.arange(0,0.1,0.01)]

    # callback function
    #eval_callback = EvalCallback(env, best_model_save_path='./logs/', log_path='./logs/', eval_freq=100, deterministic=True, render=False, verbose=1)
    new_callback = SaveOnBestTrainingRewardCallback(check_freq= checks, log_dir=monitor_dir)

    # exploration parameters
    max_epsilon = 1.0  # exploration probability at start
    min_epsilon = 0.01  # minimum exploration probability
    #decay_rate = 0.0005  # exponential decay rate for exploration prob
    timesteps = 12   # Horizon H = simulation steps per episode

    # deep learning parameters
    iters = episodes * timesteps  # number of simulation timesteps during training

    # define NN structure
    #hidden_layer_size = 256
    #policy_kwargs = dict([self.hidden_layer_size, self.hidden_layer_size])
    #layers = 2  # number of layers in NN
    policy_kwargs_v = dict( #activation_fn=th.nn.ReLU,
    net_arch=[32, 32])
    # load tensorboard log
    logdir = "60_min_2_veh"
    if not os.path.exists(logdir):
        os.makedirs(logdir)
    #tensorboard_log = "./A2C/"
    #tensorboard_log = None

    #model = PPO("MlpPolicy", env, learning_rate=0.00004, n_steps=16, batch_size=1024, n_epochs=6, gamma=0.9999, gae_lambda=0.8,
    #            clip_range=0.2, clip_range_vf=None, normalize_advantage=True, ent_coef=0.001, vf_coef=0.2, max_grad_norm=1.0,
    #            use_sde=False, sde_sample_freq=-1, target_kl=None, tensorboard_log=logdir, policy_kwargs=policy_kwargs_v, verbose=1,
    #            seed=1, device='auto', _init_setup_model=True)
    # first: evaluate model before learning
    #print("######################## EVALUATION before learning: ", evaluate(model, env, episodes=10))
    model = PPO.load("/home/niebisch/Downloads/ppo_agents/a2c_env_2_veh_60min_all_mb_4_6_four_400.zip", env=env) #"/home/niebisch/chunksimulation/ppo_env_2_veh_30min_50mb_600.zip"
    #print(model.seed)
    #sys.exit()
    #model.seed = 100
    # learn
    # start = time.time()
    # for i in range(1, 3001):
    #     model.learn(total_timesteps=100, log_interval=1, tb_log_name="PPO_60min", reset_num_timesteps=False)
    #     if i%50 == 0:
    #         model.save("ppo_env_2_veh_60min_" +str(i))
    # model.save("ppo_env_2_veh_60min")
    # elapsed_time = time.time() - start
    #
    # print("######### Model created and trained #########")
    # print("Training time:", elapsed_time)
    #
    # # create log files (.csv), get log_dict from GymEnvironment
    # log_dict = new_callback.get_log()
    # result_file = os.getcwd() + '/logs/' + 'log_dict_' + str(episodes) + '.csv'
    # with open(result_file, 'w+', newline='') as r:
    #     writer = csv.writer(r)
    #     for i in range(len(log_dict)):
    #         for episode in log_dict[i]:
    #                 writer.writerow([str(episode)])
    #                 for timestep in log_dict[i][episode]:
    #                     writer.writerow(log_dict[i][episode][timestep])
    #env.seed(5)
    #print("######################## EVALUATION after learning: ", evaluate(model, env, episodes=1))
    #sys.exit()

    policy = model.policy
    #policy.save("sac_policy_pendulum")

    # Retrieve the environment
    env = model.get_env()
    #print(env)

    import numpy as np

    print("Number Timesteps", model.num_timesteps)
    sys.exit()
    def predict_proba(model, state):
        obs = model.policy.obs_to_tensor(state)[0]
        dis = model.policy.get_distribution(obs)
        probs = dis.distribution.probs
        probs_np = probs.detach().numpy()
        return probs_np
    r = predict_proba(model, [[200,   9,  83,   3,   9,   0]])
    for i in range(4):
        r2 = predict_proba(model, [[0,  0,  0,   i,  0,   2]])
        #print(len(r[0]), r)
        #print(len(r2[0]), r2)
        l = []
        for i in r2[0]:
            l.append(i)
        #print(l)
        x = range(len(l))
        plt.figure()
        plt.plot(x, l)
    #l2 = [0.08739711, 0.032670703, 0.051324643, 0.03872226, 0.13341069, 0.0481224, 0.10457629, 0.048216883, 0.039814226, 0.100390695, 0.028055469, 0.019580508, 0.028756635, 0.012860653, 0.010056291, 0.036809105, 0.017540356, 0.007922768, 0.009583749, 0.007002305, 0.009038585, 0.0072087008, 0.0055114073, 0.008223794, 0.0044208327, 0.006203613, 0.0027170596, 0.0026753945, 0.0029047062, 0.0041410145, 0.0037697228, 0.0039457125, 0.0054341005, 0.0039249, 0.003860936, 0.0022355109, 0.0026495794, 0.0017745012, 0.002510681, 0.0020252147, 0.0015716278, 0.002655475, 0.002436621, 0.001282587, 0.00178093, 0.0019586158, 0.001227184, 0.0014682454, 0.001109996, 0.0014202212, 0.0012239849, 0.0010601863, 0.0011550689, 0.0011584368, 0.0010697361, 0.0012905721, 0.0011000342, 0.00092461926, 0.0009941404, 0.00085494545, 0.001007638, 0.0008676051, 0.00086562155, 0.00068752764, 0.00071998365, 0.0010088746, 0.0008532919, 0.0008305308, 0.0007217524, 0.00058466464, 0.0007933745, 0.00070357154, 0.00065420667, 0.00064520637, 0.00054493576, 0.00059126946, 0.00091929367, 0.00048412243, 0.0005578606, 0.00047278102, 0.00050715567, 0.0005877092, 0.00043649646, 0.00051728566, 0.00068027765, 0.00055056793, 0.0005411918, 0.00038629235, 0.0004729515, 0.0004021443, 0.00047559108, 0.00043954546, 0.0003829366, 0.0003397305, 0.0005299943, 0.00040406952, 0.00045608397, 0.00034188636, 0.00040244815, 0.00048047316, 0.00041821136]

    #plt.plot(x, l2)
    #plt.ylim(0, 0.02)
    plt.show()
    sys.exit()

    # Evaluate the policy
    mean_reward, std_reward = evaluate_policy(policy, env, n_eval_episodes=1, deterministic=False)

    print(f"mean_reward={mean_reward:.2f} +/- {std_reward}")
    env.close()
