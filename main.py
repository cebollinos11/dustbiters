import random
from typing import Dict, List, Optional, Tuple

# ------------------------
# Action abstraction
# ------------------------
class Action:
    def __init__(self, type, params=None):
        self.type = type  # "build", "drive", "draw", "end"
        self.params = params or {}

    def __repr__(self):
        return f"Action({self.type}, {self.params})"


# ------------------------
# Dustbiters Environment
# ------------------------
class DustbitersEnv:
    def __init__(self, seed=None):
        self.rng = random.Random(seed)
        self.reset()

    def reset(self):
        # Deck setup
        self.cards = [f"Car{i+1}" for i in range(21)]
        self.rng.shuffle(self.cards)

        self.convoy: List[str] = []
        self.junkyard: List[str] = []
        self.players: List[Dict] = [
            {"name": "P1", "hand": [], "convoy": []},
            {"name": "P2", "hand": [], "convoy": []},
        ]

        # Deal
        self.players[0]["convoy"] = self.cards[:4]
        self.players[1]["convoy"] = self.cards[4:8]
        self.convoy = self.players[0]["convoy"] + self.players[1]["convoy"]

        self.players[0]["hand"] = self.cards[8:12]
        self.players[1]["hand"] = self.cards[12:16]
        self.deck = self.cards[16:]

        self.turn = self.rng.choice([0, 1])
        self.actions_left = 3
        self.done = False
        self.winner: Optional[int] = None

        return self._get_obs()

    # ------------------------
    # Core Logic
    # ------------------------
    def build(self, player, card):
        if card not in player["hand"]:
            return False
        player["hand"].remove(card)
        player["convoy"].append(card)
        self.convoy.append(card)
        return True

    def drive(self, player, car, direction):
        if car not in player["convoy"]:
            return False
        idx = self.convoy.index(car)
        if direction == "f" and idx < len(self.convoy) - 1:
            self.convoy[idx], self.convoy[idx+1] = self.convoy[idx+1], self.convoy[idx]
        elif direction == "b" and idx > 0:
            self.convoy[idx], self.convoy[idx-1] = self.convoy[idx-1], self.convoy[idx]
        else:
            return False
        return True

    def draw(self, player):
        if not self.deck:
            return False
        card = self.deck.pop(0)
        player["hand"].append(card)
        return True

    def sandstorm(self):
        if not self.convoy:
            return
        destroyed = self.convoy.pop(0)
        self.junkyard.append(destroyed)
        for p in self.players:
            if destroyed in p["convoy"]:
                p["convoy"].remove(destroyed)

    def check_win(self):
        for i, p in enumerate(self.players):
            if not p["convoy"]:
                return 1 - i
        return None

    def apply_action(self, player, action: Action):
        if action.type == "build":
            return self.build(player, action.params.get("card"))
        elif action.type == "drive":
            return self.drive(
                player,
                action.params.get("car"),
                action.params.get("direction"),
            )
        elif action.type == "draw":
            return self.draw(player)
        elif action.type == "end":
            return True
        return False

    # ------------------------
    # Step function (for AI training)
    # ------------------------
    def step(self, action: Action):
        if self.done:
            raise ValueError("Game already finished!")

        player = self.players[self.turn]
        valid = self.apply_action(player, action)

        reward = 0
        if valid:
            if action.type != "end":
                self.actions_left -= 1
        else:
            reward -= 1  # small penalty for invalid

        if action.type == "end" or self.actions_left == 0:
            self.sandstorm()
            self.winner = self.check_win()
            if self.winner is not None:
                self.done = True
                reward = 1 if self.winner == self.turn else -1
            else:
                self.turn = 1 - self.turn
                self.actions_left = 3

        return self._get_obs(), reward, self.done, {}

    # ------------------------
    # Observation space
    # ------------------------
    def _get_obs(self):
        """Return a dict observation (can later be encoded into tensors)."""
        return {
            "turn": self.turn,
            "actions_left": self.actions_left,
            "deck_size": len(self.deck),
            "convoy": list(self.convoy),
            "hands": [list(p["hand"]) for p in self.players],
            "convoys": [list(p["convoy"]) for p in self.players],
        }

    # ------------------------
    # Available moves
    # ------------------------
    def legal_actions(self):
        """Return all legal actions for current player."""
        player = self.players[self.turn]
        actions = []

        # Build
        for c in player["hand"]:
            actions.append(Action("build", {"card": c}))

        # Drive
        for c in player["convoy"]:
            actions.append(Action("drive", {"car": c, "direction": "f"}))
            actions.append(Action("drive", {"car": c, "direction": "b"}))

        # Draw
        if self.deck:
            actions.append(Action("draw"))

        # End
        actions.append(Action("end"))
        return actions


import gymnasium as gym
from gymnasium import spaces
import numpy as np

class DustbitersGym(gym.Env):
    def __init__(self, seed=None):
        super().__init__()
        self.env = DustbitersEnv(seed=seed)

        # We’ll cap at 50 possible moves (simplification)
        self.max_actions = 50  

        # Action space: int index into legal_actions()
        self.action_space = spaces.Discrete(self.max_actions)

        # Observation space (very rough encoding)
        # convoy size max=21, each card -> integer id
        # Represent state as a vector of fixed length (pad with -1)
        self.max_cards = 21
        self.observation_space = spaces.Box(
            low=-1, high=self.max_cards,
            shape=(self.max_cards * 3 + 3,), dtype=np.int32
        )

    def reset(self, *, seed=None, options=None):
        obs = self.env.reset()
        return self._encode_obs(obs), {}

    def step(self, action_idx):
        legal = self.env.legal_actions()
        if action_idx >= len(legal):
            # If invalid, punish
            obs, reward, done, info = self.env.step(Action("end"))
            return self._encode_obs(obs), -1, done, False, info

        action = legal[action_idx]
        obs, reward, done, info = self.env.step(action)
        return self._encode_obs(obs), reward, done, False, info

    def _encode_obs(self, obs_dict):
        """Convert dict into flat array of ints."""
        card2id = {f"Car{i+1}": i for i in range(self.max_cards)}

        def encode_list(cards, length):
            return [card2id[c] for c in cards] + [-1] * (length - len(cards))

        # fixed padding
        convoy_enc = encode_list(obs_dict["convoy"], self.max_cards)
        hand0_enc = encode_list(obs_dict["hands"][0], self.max_cards)
        hand1_enc = encode_list(obs_dict["hands"][1], self.max_cards)

        meta = [obs_dict["turn"], obs_dict["actions_left"], obs_dict["deck_size"]]

        return np.array(convoy_enc + hand0_enc + hand1_enc + meta, dtype=np.int32)


#### Train
# print("training ");

# from stable_baselines3 import PPO

# env = DustbitersGym(seed=42)

# model = PPO("MlpPolicy", env, verbose=1)
# model.learn(total_timesteps=1_000)  # adjust as needed

# model.save("dustbiters_ppo")
# print("done");


####    

from stable_baselines3 import PPO

# Load trained model
model = PPO.load("dustbiters_ppo")
env = DustbitersGym()

obs, _ = env.reset()
done = False

human_player = 0  # let you be Player 0

while not done:
    if env.env.turn == human_player:
        # Show state
        print("\nYour turn!")
        print("Hand:", env.env.players[human_player]["hand"])
        print("Convoy:", env.env.convoy)

        legal = env.env.legal_actions()
        for i, a in enumerate(legal):
            print(f"{i}: {a}")

        choice = int(input("Choose action: "))
        obs, reward, done, _, _ = env.step(choice)
    else:
# Agent's move
        legal = env.env.legal_actions()   # snapshot legal moves BEFORE stepping
        action, _ = model.predict(obs)

        # just in case model picks something invalid (like padding index)
        if action >= len(legal):
            chosen_action = legal[-1]  # fallback: pick last legal action
        else:
            chosen_action = legal[action]

        print(f"AI played: {chosen_action}")

        obs, reward, done, _, _ = env.step(action)

winner = env.env.winner
print("Game Over!")
if winner == human_player:
    print("You win!")
else:
    print("AI wins!")
