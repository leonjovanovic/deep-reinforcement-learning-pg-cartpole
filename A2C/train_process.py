import gym
import torch
import numpy as np

from collections import namedtuple
Memory = namedtuple('Memory', ['obs', 'action', 'new_obs', 'reward', 'entropy'])

def train_process(hyperparameters, rank, shared_model_actor, memory, obs):
    # Create enviroment and agent
    env = gym.make(hyperparameters['env_name'])
    device = 'cpu'# 'cuda' if torch.cuda.is_available() else 'cpu'
    ep_memory = []
    obs = obs
    print("Starting process " + str(rank) + str("..."))
    for n_counter in range(hyperparameters['n-step']):
        # Choose action by getting probabilities from ActorNN
        # We send current state as NN input and get two probabilities for each action (in sum of 1)
        action_prob = shared_model_actor(torch.tensor(obs, dtype=torch.double).to(device))
        # We dont take higher probability but take random value of 0 or 1 based on probabilities from NN
        action = np.random.choice(np.array([0, 1]), p=action_prob.cpu().data.numpy())
        # Add sum of probability*log(probability) to list so we can count mean of list when we calculate loss
        # We detach grads since we dont need them when we do loss.backwards() in future
        entropy = 0
        if hyperparameters["entropy_flag"]:
            entropy = -hyperparameters["entropy_coef"] * torch.sum(action_prob * torch.log(action_prob)).detach()
        # Execute chosen action and retrieve new state, reward and if its terminal state
        new_obs, reward, done, _ = env.step(action)
        # To make loss more unrewarding we penalize loss more (instead of default 0)
        if done:
            reward = -20
        ep_memory.append(Memory(obs=obs, action=action, new_obs=new_obs, reward=reward, entropy=entropy))
        # Change new state to be current state so we can continue
        obs = new_obs
        # If we are at the end of episode (terminal state)
        if done:
            break
    memory.put(ep_memory)
    # Process will end if test process alerted train processes that we reached goal
    print("Process " + str(rank) + " ended!")
    env.close()
