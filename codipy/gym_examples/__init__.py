from gym.envs.registration import register

register(
    id="gym_examples/Chunksimulation-v2",
    entry_point="gym_examples.envs:env_v2",
    max_episode_steps=8,
)

register(
    id="gym_examples/Chunksimulation-v3",
    entry_point="gym_examples.envs:env_v3",
    max_episode_steps=8,
)
register(
    id="gym_examples/Chunksimulation-v4",
    entry_point="gym_examples.envs:env_v4",
    max_episode_steps=8,
)
register(
    id="gym_examples/Chunksimulation-v0",
    entry_point="gym_examples.envs:chunksimulation_env",
    max_episode_steps=8,
)
register(
    id="gym_examples/Chunksimulation-A2C-v0",
    entry_point="gym_examples.envs:env_a2c",
    max_episode_steps=8,
)
register(
    id="gym_examples/Chunksimulation-A2C-v2",
    entry_point="gym_examples.envs:env_a2c_v2",
    max_episode_steps=12,
)
