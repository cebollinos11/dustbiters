import random
import curses

# ------------------------
# Action abstraction
# ------------------------
class Action:
    def __init__(self, type, params=None):
        self.type = type  # "build", "drive", "draw", "end"
        self.params = params or {}

# ------------------------
# Dustbiters Game
# ------------------------
class Dustbiters:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        curses.curs_set(0)
        self.stdscr.clear()

        # Colors
        curses.start_color()
        curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)   # Player 1
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK) # Player 2

        # Deck setup
        self.cards = [f"Car{i+1}" for i in range(21)]
        random.shuffle(self.cards)

        self.convoy = []
        self.junkyard = []
        self.players = [
            {"name": "Player 1", "hand": [], "convoy": [], "color": 1},
            {"name": "Player 2", "hand": [], "convoy": [], "color": 2},
        ]

        # Deal cards
        self.players[0]["convoy"] = self.cards[:4]
        self.players[1]["convoy"] = self.cards[4:8]
        self.convoy = self.players[0]["convoy"] + self.players[1]["convoy"]

        self.players[0]["hand"] = self.cards[8:12]
        self.players[1]["hand"] = self.cards[12:16]
        self.deck = self.cards[16:]

        self.turn = random.choice([0, 1])

        # Windows
        height, width = self.stdscr.getmaxyx()
        convoy_width = width // 4
        player_width = width // 2
        msg_width = width - (convoy_width + player_width)
        log_height = max(5, height - 6)
        input_height = 6

        self.win_convoy = curses.newwin(height, convoy_width, 0, 0)
        self.win_hand = curses.newwin(height, player_width, 0, convoy_width)
        self.win_log = curses.newwin(log_height, msg_width, 0, convoy_width + player_width)
        self.win_input = curses.newwin(input_height, msg_width, log_height, convoy_width + player_width)

        self.log_messages = []

    # ------------------------
    # Logging and UI
    # ------------------------
    def add_log(self, text):
        max_lines = max(1, self.win_log.getmaxyx()[0] - 2)
        self.log_messages.append(text)
        if len(self.log_messages) > max_lines:
            self.log_messages = self.log_messages[-max_lines:]

    def draw_screen(self, message="", message_color=None):
        for w in (self.win_convoy, self.win_hand, self.win_log, self.win_input):
            w.clear()

        # Convoy (front -> back)
        self.win_convoy.addstr(1, 1, "CONVOY (Front -> Back):")
        y = 2
        for display_idx, car in enumerate(reversed(self.convoy)):
            color = None
            for p in self.players:
                if car in p["convoy"]:
                    color = p["color"]
                    break
            line_text = f"[{display_idx+1}] {car}"
            if color:
                self.win_convoy.attron(curses.color_pair(color))
                self.win_convoy.addstr(y, 1, line_text)
                self.win_convoy.attroff(curses.color_pair(color))
            else:
                self.win_convoy.addstr(y, 1, line_text)
            y += 1

        # Hands
        y = 1
        for p in self.players:
            self.win_hand.attron(curses.color_pair(p["color"]))
            self.win_hand.addstr(y, 1, f"{p['name']} Hand:")
            self.win_hand.attroff(curses.color_pair(p["color"]))
            for i, card in enumerate(p["hand"]):
                self.win_hand.addstr(y + i + 1, 3, f"[{i+1}] {card}")
            y += len(p["hand"]) + 2

        # Log
        self.win_log.addstr(0, 1, "Event Log:")
        y = 1
        for msg in self.log_messages:
            self.win_log.addstr(y, 1, msg[: self.win_log.getmaxyx()[1] - 3])
            y += 1

        # Input message
        if message:
            if message_color:
                self.win_input.attron(curses.color_pair(message_color))
                self.win_input.addstr(1, 1, message[: self.win_input.getmaxyx()[1] - 3])
                self.win_input.attroff(curses.color_pair(message_color))
            else:
                self.win_input.addstr(1, 1, message[: self.win_input.getmaxyx()[1] - 3])

        # Borders
        for w in (self.win_convoy, self.win_hand, self.win_log, self.win_input):
            w.box()
            w.refresh()

    def get_input(self, prompt):
        self.draw_screen(prompt)
        curses.echo()
        maxy, maxx = self.win_input.getmaxyx()
        self.win_input.addstr(2, 1, "> ")
        self.win_input.refresh()
        input_bytes = self.win_input.getstr(2, 3, max(1, maxx - 4))
        curses.noecho()
        input_str = input_bytes.decode("utf-8").strip() if input_bytes else ""
        self.draw_screen()
        return input_str

    # ------------------------
    # Pure Game Logic
    # ------------------------
    def build(self, player, card):
        if card not in player["hand"]:
            return False
        player["hand"].remove(card)
        player["convoy"].append(card)
        self.convoy.append(card)
        self.add_log(f"{player['name']} built {card}")
        return True

    def drive(self, player, car, direction):
        if car not in player["convoy"]:
            return False
        idx = self.convoy.index(car)
        if direction == "f" and idx < len(self.convoy) - 1:
            self.convoy[idx], self.convoy[idx+1] = self.convoy[idx+1], self.convoy[idx]
            self.add_log(f"{player['name']} moved {car} forward")
        elif direction == "b" and idx > 0:
            self.convoy[idx], self.convoy[idx-1] = self.convoy[idx-1], self.convoy[idx]
            self.add_log(f"{player['name']} moved {car} backward")
        else:
            return False
        return True

    def draw(self, player):
        if not self.deck:
            return False
        card = self.deck.pop(0)
        player["hand"].append(card)
        self.add_log(f"{player['name']} drew {card}")
        return True

    def sandstorm(self):
        if not self.convoy:
            return
        destroyed = self.convoy.pop(0)
        self.junkyard.append(destroyed)
        for p in self.players:
            if destroyed in p["convoy"]:
                p["convoy"].remove(destroyed)
        self.add_log(f"Sandstorm destroyed {destroyed}")

    def check_win(self):
        for i, p in enumerate(self.players):
            if not p["convoy"]:
                return 1 - i
        return None

    def apply_action(self, player, action: Action):
        if action.type == "invalid":
            return False
        if action.type == "build":
            return self.build(player, action.params.get("card"))
        elif action.type == "drive":
            return self.drive(player,
                              action.params.get("car"),
                              action.params.get("direction"))
        elif action.type == "draw":
            return self.draw(player)
        elif action.type == "end":
            return True
        else:
            self.add_log(f"Unknown action: {action.type}")
            return False

    # ------------------------
    # Turn Loop
    # ------------------------
    def take_turn(self, policy):
        player = self.players[self.turn]
        actions = 3
        while actions > 0:
            self.draw_screen(f"{player['name']}'s turn. Actions left: {actions}",
                             message_color=player["color"])
            action = policy(self, player, actions)
            success = self.apply_action(player, action)
            if action.type == "end":
                break
            if success:
                actions -= 1

        self.sandstorm()
        winner = self.check_win()
        if winner is not None:
            self.add_log(f"{self.players[winner]['name']} wins!")
            self.draw_screen("Game over")
            self.get_input("Press Enter to exit...")
            return True
        self.turn = 1 - self.turn
        return False

    def play(self, policies):
        game_over = False
        while not game_over:
            game_over = self.take_turn(policies[self.turn])

# ------------------------
# Policies (Human & AI)
# ------------------------
def human_policy(game, player, actions_left):
    while True:
        choice = game.get_input(
            "Commands: b N=build hand[N], d=draw, a N=forward, r N=backward, e=end"
        ).lower().split()

        if not choice:
            game.add_log("Empty input! Try again.")
            game.draw_screen()
            continue

        cmd = choice[0]
        arg = int(choice[1]) - 1 if len(choice) > 1 and choice[1].isdigit() else None

        if cmd == "b":  # build
            if not player["hand"]:
                game.add_log("No cards to build!")
                return Action("invalid")
            if arg is None or arg < 0 or arg >= len(player["hand"]):
                game.add_log("Invalid card index!")
                return Action("invalid")
            return Action("build", {"card": player["hand"][arg]})

        elif cmd in ("a", "r"):  # accelerate/reverse
            if not player["convoy"]:
                game.add_log("No cars to move!")
                return Action("invalid")
            if arg is None or arg < 0 or arg >= len(player["convoy"]):
                game.add_log("Invalid car index!")
                return Action("invalid")

            # Map display index (front=1) to convoy car
            car = list(reversed(player["convoy"]))[arg]
            direction = "f" if cmd == "a" else "b"
            return Action("drive", {"car": car, "direction": direction})

        elif cmd == "d":
            return Action("draw")

        elif cmd == "e":
            return Action("end")

        else:
            game.add_log("Invalid input! Try again.")
            game.draw_screen()

def random_ai_policy(game, player, actions_left):
    options = ["build", "drive", "draw", "end"]
    choice = random.choice(options)
    if choice == "build" and player["hand"]:
        return Action("build", {"card": random.choice(player["hand"])})
    if choice == "drive" and player["convoy"]:
        return Action("drive", {"car": random.choice(player["convoy"]),
                                "direction": random.choice(["f","b"])})
    if choice == "draw" and game.deck:
        return Action("draw")
    return Action("end")

# ------------------------
# Main
# ------------------------
def main(stdscr):
    game = Dustbiters(stdscr)
    policies = [human_policy, random_ai_policy]
    game.play(policies)

if __name__ == "__main__":
    curses.wrapper(main)
