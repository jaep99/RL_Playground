import gymnasium as gym
from stable_baselines3 import SAC, TD3, A2C
import os
import argparse
import custom_gym.envs.mujoco
from stable_baselines3.common.callbacks import EvalCallback 
from stable_baselines3.common.callbacks import BaseCallback
import datetime
import numpy as np
import matplotlib.pyplot as plt
import numpy as np

class PlottingCallback(BaseCallback):
    def __init__(self, env, ax1, fig, verbose=0):
        super(PlottingCallback, self).__init__(verbose)
        self.env = env
        self.ax1 = ax1
        self.fig = fig
        self.last_episode_count = 0

        # Print to check the environment instance
        #print(f"Environment in Callback: {id(self.wrapped_env)}", flush=True)
    
    def _on_step(self) -> bool:
        print(f"Current episodes list: {self.env.episodes}", flush=True)  # Add this to debug
        # Check if a new episode is logged in the environment
        if len(self.env.episodes) > self.last_episode_count:
            print("Calling update_plot...", flush=True)  # Add this for debugging
            self.last_episode_count = len(self.env.episodes)
            # Update the plot with the latest data
            update_plot(self.env, self.ax1, self.fig)
        return True
    
# Create directories to hold models and logs
model_dir = "models"
log_dir = "logs"
os.makedirs(model_dir, exist_ok=True)
os.makedirs(log_dir, exist_ok=True)

# Max episode steps added
MAX_EPISODE_STEPS = 100

def train(env, sb3_algo):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_name = f"{sb3_algo}_{timestamp}"

    # Create separated environment for model evaluation
    eval_env = gym.make('InvertedPendulum3D-v1-newplot', render_mode=None, max_episode_steps=MAX_EPISODE_STEPS)
    
    # EvalCallback added
    eval_callback = EvalCallback(eval_env, best_model_save_path=f"{model_dir}/best_{run_name}",
                                 log_path=log_dir, eval_freq=10000,
                                 deterministic=True, render=False)

    match sb3_algo:
        case 'SAC':
            model = SAC('MlpPolicy', env, verbose=1, device='cuda', tensorboard_log=log_dir)
        case 'TD3':
            model = TD3('MlpPolicy', env, verbose=1, device='cuda', tensorboard_log=log_dir)
        case 'A2C':
            model = A2C('MlpPolicy', env, verbose=1, device='cuda', tensorboard_log=log_dir)
        case _:
            print('Algorithm not found')
            return

    TIMESTEPS = 1000
    #total_timesteps = 0
    #max_timesteps = 3000 * 100 # 3000 steps * 100 iterations
    iters = 0

    plt.ion()
    fig, (ax1) = plt.subplots(1, 1, figsize = (8,6))
    plt.show(block=False)

    plotting_callback = PlottingCallback(env, ax1, fig)

    combined_callbacks = [eval_callback, plotting_callback]

    while True:
        try:
            iters += 1
            # eval_callback added
            model.learn(total_timesteps=TIMESTEPS, reset_num_timesteps=False, tb_log_name=run_name, callback=combined_callbacks)
            model.save(f"{model_dir}/{run_name}_{TIMESTEPS*iters}")
            
            #total_timesteps += TIMESTEPS
            #print(f"Total timesteps: {total_timesteps}")
        except Exception as e:
            print(f"Unexpected error in training loop: {e}")
    plt.ioff()
    plt.show()
    #print("Training completed after reaching 300000 timesteps.")

def update_plot(env, ax1, fig):
    # Clear previous data
    ax1.clear()

    # Plot using episode mean data
    ax1.plot(env.episodes, env.episode_rewards, label='Student Reward Mean')
    ax1.set_xlabel('Episode')
    ax1.set_ylabel('Mean Reward')
    ax1.set_title('Student Mean Reward over Episodes')
    ax1.legend()

    # Redraw the plots
    # Force update of the canvas
    fig.canvas.draw()
    fig.canvas.flush_events()
    plt.pause(0.1)

def test(env, sb3_algo, path_to_model, num_episodes=30):
    match sb3_algo:
        case 'SAC':
            model = SAC.load(path_to_model, env=env)
        case 'TD3':
            model = TD3.load(path_to_model, env=env)
        case 'A2C':
            model = A2C.load(path_to_model, env=env)
        case _:
            print('Algorithm not found')
            return

    episode_rewards = []
    episode_lengths = []

    for episode in range(num_episodes):
        obs, _ = env.reset()
        terminated = truncated = False
        total_reward = 0
        step_count = 0

        print(f"\nEpisode {episode + 1}")

        while not (terminated or truncated) and step_count < MAX_EPISODE_STEPS:
            action, _ = model.predict(obs)
            obs, reward, terminated, truncated, info = env.step(action)
            env.render()

            total_reward += reward
            step_count += 1

            if step_count % 1000 == 0:  # Print info every 1000 steps
                cart_x, cart_y = obs[0], obs[1]
                print(f"Step: {step_count}, Reward: {reward:.4f}, Angle: {info.get('angle', 'N/A'):.4f}, Position: ({cart_x:.4f}, {cart_y:.4f})")

        episode_rewards.append(total_reward)
        episode_lengths.append(step_count)

        print(f"Episode {episode + 1} finished after {step_count} steps")
        print(f"Total reward: {total_reward}")
        print(f"Average reward per step: {total_reward / step_count}")

    print("\nTest Summary:")
    print(f"Average episode reward: {np.mean(episode_rewards):.2f} ± {np.std(episode_rewards):.2f}")
    print(f"Average episode length: {np.mean(episode_lengths):.2f} ± {np.std(episode_lengths):.2f}")
    print(f"Number of episodes reaching max steps: {sum([1 for length in episode_lengths if length == MAX_EPISODE_STEPS])}")

if __name__ == '__main__':
    # Parse command line inputs
    import matplotlib
    matplotlib.use('TkAgg')

    parser = argparse.ArgumentParser(description='Train or test model.')
    parser.add_argument('sb3_algo', help='StableBaseline3 RL algorithm i.e. SAC, TD3')
    parser.add_argument('-train', '--train', action='store_true')
    parser.add_argument('-test', '--test', metavar='path_to_model')
    args = parser.parse_args()

    if args.train:
        gymenv = gym.make('InvertedPendulum3D-v1-newplot', render_mode=None, max_episode_steps=MAX_EPISODE_STEPS)
        train(gymenv, args.sb3_algo)

    if args.test:
        if os.path.isfile(args.test):
            gymenv = gym.make('InvertedPendulum3D-v1-newplot', render_mode='human', max_episode_steps=MAX_EPISODE_STEPS)
            test(gymenv, args.sb3_algo, path_to_model=args.test)
        else:
            print(f'{args.test} not found.')