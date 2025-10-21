import random
import bisect
import copy
import itertools
import sys

import matplotlib.pyplot as plt
import math
import csv
import json
import os
from os import walk
import pandas as pd
import xmltodict as xdict
from os import listdir
from os.path import isfile, join
import parameter_parser
from cycler import cycler
from mpl_toolkits.axes_grid1.inset_locator import zoomed_inset_axes, mark_inset
import mpl_toolkits.axes_grid1.inset_locator as il
import matplotlib.patches as mpatches
import numpy as np

plt.style.use(['science', 'ieee', 'grid', 'high-vis'])
plt.rc('text', usetex=False)
plt.rcParams['pdf.fonttype'] = 42
plt.rcParams['ps.fonttype'] = 42
random.seed(0)
def calc_rewards():
    timesteps = 8
    max_chunks = 7088.0
    cost_value = float(1.0/max_chunks)
    sum_seeded = 0
    step = 0
    state = 0
    acc_reward = 0.0
    acc_action = 0
    flag = False
    total_seeded = 0
    while step < 8:
        action = random.randint(0, 21)
        if sum_seeded < max_chunks:
            state = random.randint(state, max_chunks)
        else:
            state = max_chunks
        seeding_number = int(action * 0.01 * max_chunks)
        sum_seeded += seeding_number
        sum_seeded = min(sum_seeded, max_chunks)
        #print(timestep_counter, state, done, timesteps)
        # Save step information

        if state == max_chunks or state + seeding_number > max_chunks:
            reward = 0.0
            total_seeded = sum_seeded + (max_chunks - state)
        elif step == 7:
            if max_chunks - state != 0:
                flag = True
            reward = ((1.0 - round((((sum_seeded + max_chunks - state)) * cost_value), 10) )  \
                            + ((1.0 - round((max_chunks - state) * cost_value, 10)) ))
            total_seeded = sum_seeded + (max_chunks - state)
                                 #+ round((max_chunks - state) * cost_value, 4))
        else:
            #costs = round(((total_seed + max_chunks - state) * cost_value), 4)
            #reward = round((1-costs), 4)
            reward =  round(1.0 - (((sum_seeded + max_chunks - state)) * cost_value), 10)
        acc_reward += reward
        acc_action += action
        step += 1
        #print(acc_reward, reward, action, sum_seeded, state)
    #if acc_reward >= 1.0:
    #    print(acc_reward, acc_action)
    #    sys.exit()
    #print()
    return acc_reward, acc_action, flag, total_seeded

rew_results_n = []
act_rewards_n = []
rew_results = []
act_rewards = []
seeded = []
seeded_n = []
flags = []
iters = range(100000)
for i in iters:
    rew, act, flag, total_seeded = calc_rewards()
    if flag:
        rew_results.append(rew)
        act_rewards.append(act)
        seeded.append(total_seeded)
    else:
        rew_results_n.append(rew)
        act_rewards_n.append(act)
        seeded_n.append(total_seeded)
plt.figure()
plt.scatter(act_rewards_n, rew_results_n, color='blue', marker=".")
plt.scatter(act_rewards, rew_results, color='red', marker=".")


plt.show()
