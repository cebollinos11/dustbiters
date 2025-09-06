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

        # Windows: left (convoy), middle (hands+convoys), right (messages)
        height, width = self.stdscr.getmaxyx()
        convoy_width = width // 4
        player_width = width // 2
        msg_width = width - (convoy_width + player_width)

        self.win_convoy = curses.newwin(height, convoy_width, 0, 0)
        self.win_hand = curses.newwin(height, player_width, 0, convoy_width)
        self.win_msg = curses.newwin(height, msg_width, 0, convoy_width + player_width)

    def draw_screen(self, message=""):
        self.win_convoy.clear()
        self.win_hand.clear()
        self.win_msg.clear()

        # Convoy (vertical list)
        try:
            self.win_convoy.addstr(1, 1, "CONVOY (Back -> Front):")
        except curses.error:
            pass

        y = 2
        for i, car in enumerate(self.convoy):
            color = None
            for p in self.players:
                if car in p["convoy"]:
                    color = p["color"]
                    break
            try:
                line_text = f"{i}: {car}"  # add index before car name
                if color:
                    self.win_convoy.attron(curses.color_pair(color))
                    self.win_convoy.addstr(y, 1, line_text)
                    self.win_convoy.attroff(curses.color_pair(color))
                else:
                    self.win_convoy.addstr(y, 1, line_text)
            except curses.error:
                pass
            y += 1

        # Players' hands and convoys (stacked vertically in the middle)
        y = 1
        for p in self.players:
            try:
                self.win_hand.attron(curses.color_pair(p["color"]))
                self.win_hand.addstr(y, 1, f"{p['name']} Hand:")
                for i, card in enumerate(p["hand"]):
                    self.win_hand.addstr(y + i + 1, 3, card)
                y += len(p["hand"]) + 2

                # self.win_hand.addstr(y, 1, "Convoy:")
                # for i, car in enumerate(p["convoy"]):
                #     self.win_hand.addstr(y + i + 1, 3, car)
                # y += len(p["convoy"]) + 3
                # self.win_hand.attroff(curses.color_pair(p["color"]))
            except curses.error:
                pass

        # Messages
        if message:
            try:
                self.win_msg.addstr(1, 1, message)
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
