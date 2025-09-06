import random
import curses

class Dustbiters:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        curses.curs_set(0)
        self.stdscr.clear()

        # Enable color
        curses.start_color()
        curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)   # Player 1 = Red
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK) # Player 2 = Green

        self.cards = [f"Car{i+1}" for i in range(21)]
        random.shuffle(self.cards)

        # Deal initial setup
        self.convoy = []
        self.junkyard = []

        self.players = [
            {"name": "Player 1", "hand": [], "convoy": [], "color": 1},
            {"name": "Player 2", "hand": [], "convoy": [], "color": 2},
        ]

        self.players[0]["convoy"] = self.cards[:4]
        self.players[1]["convoy"] = self.cards[4:8]
        self.convoy = self.players[0]["convoy"] + self.players[1]["convoy"]

        self.players[0]["hand"] = self.cards[8:12]
        self.players[1]["hand"] = self.cards[12:16]

        self.deck = self.cards[16:]

        self.turn = random.choice([0, 1])

        # Windows: top (convoy), middle (hand), bottom (messages)
        height, width = self.stdscr.getmaxyx()
        self.win_convoy = curses.newwin(5, width, 0, 0)
        self.win_hand = curses.newwin(7, width, 6, 0)
        self.win_msg = curses.newwin(height - 13, width, 13, 0)

    def draw_screen(self, message=""):
        self.win_convoy.clear()
        self.win_hand.clear()
        self.win_msg.clear()

        # Convoy header
        try:
            self.win_convoy.addstr(0, 0, "CONVOY (Back -> Front):")
        except curses.error:
            pass

        # Print each car in the convoy, coloring by owner
        x = 0
        y = 1
        for i, car in enumerate(self.convoy):
            # determine owner color (first matching player)
            color = None
            for p in self.players:
                if car in p["convoy"]:
                    color = p.get("color")
                    break

            try:
                if color:
                    self.win_convoy.attron(curses.color_pair(color))
                    self.win_convoy.addstr(y, x, car)
                    self.win_convoy.attroff(curses.color_pair(color))
                else:
                    self.win_convoy.addstr(y, x, car)
            except curses.error:
                # ignore if text runs off-window
                pass

            x += len(car)
            # separator between cars
            if i != len(self.convoy) - 1:
                sep = " - "
                try:
                    self.win_convoy.addstr(y, x, sep)
                except curses.error:
                    pass
                x += len(sep)

        # Hands and per-player convoy (colored)
        for i, p in enumerate(self.players):
            hand_str = " ".join(p["hand"])
            convoy_str = " ".join(p["convoy"])
            try:
                self.win_hand.attron(curses.color_pair(p["color"]))
                self.win_hand.addstr(i * 3, 0, f"{p['name']} Hand: {hand_str}")
                self.win_hand.addstr(i * 3 + 1, 0, f"Convoy: {convoy_str}")
                self.win_hand.attroff(curses.color_pair(p["color"]))
            except curses.error:
                pass

        # Message/Input
        if message:
            try:
                self.win_msg.addstr(0, 0, message)
            except curses.error:
                pass

        self.win_convoy.box()
        self.win_hand.box()
        self.win_msg.box()

        self.win_convoy.refresh()
        self.win_hand.refresh()
        self.win_msg.refresh()

    def get_input(self, prompt):
        self.win_msg.clear()
        self.win_msg.box()
        self.win_msg.addstr(1, 1, prompt)
        self.win_msg.refresh()
        curses.echo()
        input_str = self.win_msg.getstr(2, 1).decode("utf-8").strip()
        curses.noecho()
        return input_str

    def build(self, player):
        if not player["hand"]:
            self.draw_screen("No cards in hand to build!")
            return False
        choice = self.get_input(f"Choose a card to build from {player['hand']}: ")
        if choice not in player["hand"]:
            self.draw_screen("Invalid choice!")
            return False
        player["hand"].remove(choice)
        player["convoy"].append(choice)
        self.convoy.append(choice)
        return True

    def drive(self, player):
        if not player["convoy"]:
            self.draw_screen("No cars to drive!")
            return False
        choice = self.get_input(f"Choose a car to drive from {player['convoy']}: ")
        if choice not in player["convoy"]:
            self.draw_screen("Invalid choice!")
            return False
        idx = self.convoy.index(choice)
        direction = self.get_input("Move forward (f) or backward (b)? ").lower()
        if direction == "f" and idx < len(self.convoy) - 1:
            self.convoy[idx], self.convoy[idx+1] = self.convoy[idx+1], self.convoy[idx]
        elif direction == "b" and idx > 0:
            self.convoy[idx], self.convoy[idx-1] = self.convoy[idx-1], self.convoy[idx]
        else:
            self.draw_screen("Can't move that way!")
            return False
        return True

    def draw(self, player):
        if not self.deck:
            self.draw_screen("Deck empty!")
            return False
        card = self.deck.pop(0)
        player["hand"].append(card)
        self.draw_screen(f"Drew card: {card}")
        return True

    def sandstorm(self):
        if not self.convoy:
            return
        destroyed = self.convoy.pop(0)
        self.junkyard.append(destroyed)
        for p in self.players:
            if destroyed in p["convoy"]:
                p["convoy"].remove(destroyed)
        self.draw_screen(f"Sandstorm destroyed: {destroyed}")

    def check_win(self):
        for i, p in enumerate(self.players):
            if not p["convoy"]:
                return 1 - i
        return None

    def take_turn(self):
        player = self.players[self.turn]
        actions = 3
        while actions > 0:
            # color message window for current player
            try:
                self.win_msg.attron(curses.color_pair(player["color"]))
            except curses.error:
                pass

            self.draw_screen(f"{player['name']}'s turn. Actions left: {actions}")

            try:
                self.win_msg.attroff(curses.color_pair(player["color"]))
            except curses.error:
                pass

            choice = self.get_input("Choose action (build/drive/draw/end): ").lower()
            success = False
            if choice == "build":
                success = self.build(player)
            elif choice == "drive":
                success = self.drive(player)
            elif choice == "draw":
                success = self.draw(player)
            elif choice == "end":
                break
            if success:
                actions -= 1
        self.sandstorm()
        winner = self.check_win()
        if winner is not None:
            self.draw_screen(f"{self.players[winner]['name']} wins!")
            self.get_input("Press Enter to exit...")
            return True
        self.turn = 1 - self.turn
        return False

    def play(self):
        game_over = False
        while not game_over:
            game_over = self.take_turn()


def main(stdscr):
    game = Dustbiters(stdscr)
    game.play()

if __name__ == "__main__":
    curses.wrapper(main)
