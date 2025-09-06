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

        # Windows: left (convoy), middle (hands), right (log + input)
        height, width = self.stdscr.getmaxyx()
        convoy_width = width // 4
        player_width = width // 2
        msg_width = width - (convoy_width + player_width)

        # split right column: log + input
        log_height = max(5, height - 6)   # leave some room for input; min height guard
        input_height = 6

        self.win_convoy = curses.newwin(height, convoy_width, 0, 0)
        self.win_hand = curses.newwin(height, player_width, 0, convoy_width)
        self.win_log = curses.newwin(log_height, msg_width, 0, convoy_width + player_width)
        self.win_input = curses.newwin(input_height, msg_width, log_height, convoy_width + player_width)

        self.log_messages = []  # keep past actions here

    def add_log(self, text):
        # Truncate to log window height - 2 for borders/header
        max_lines = max(1, self.win_log.getmaxyx()[0] - 2)
        self.log_messages.append(text)
        if len(self.log_messages) > max_lines:
            # drop oldest lines
            self.log_messages = self.log_messages[-max_lines:]

    def draw_screen(self, message="", message_color=None):
        # Clear windows
        for w in (self.win_convoy, self.win_hand, self.win_log, self.win_input):
            try:
                w.clear()
            except curses.error:
                pass

        # Convoy
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
                line_text = f"{i}: {car}"
                if color:
                    self.win_convoy.attron(curses.color_pair(color))
                    self.win_convoy.addstr(y, 1, line_text)
                    self.win_convoy.attroff(curses.color_pair(color))
                else:
                    self.win_convoy.addstr(y, 1, line_text)
            except curses.error:
                pass
            y += 1

        # Players' hands (middle)
        y = 1
        for p in self.players:
            try:
                self.win_hand.attron(curses.color_pair(p["color"]))
                self.win_hand.addstr(y, 1, f"{p['name']} Hand:")
                self.win_hand.attroff(curses.color_pair(p["color"]))
                for i, card in enumerate(p["hand"]):
                    self.win_hand.addstr(y + i + 1, 3, card)
                y += len(p["hand"]) + 2
            except curses.error:
                pass

        # Log window
        try:
            self.win_log.addstr(0, 1, "Event Log:")
        except curses.error:
            pass
        y = 1
        for msg in self.log_messages:
            try:
                # ensure we don't write past window
                self.win_log.addstr(y, 1, msg[: self.win_log.getmaxyx()[1] - 3])
            except curses.error:
                pass
            y += 1

        # Input window: show message/prompt at top of input area
        try:
            if message and message_color:
                self.win_input.attron(curses.color_pair(message_color))
                self.win_input.addstr(1, 1, message[: self.win_input.getmaxyx()[1] - 3])
                self.win_input.attroff(curses.color_pair(message_color))
            elif message:
                self.win_input.addstr(1, 1, message[: self.win_input.getmaxyx()[1] - 3])
        except curses.error:
            pass

        # Draw borders and refresh
        try:
            self.win_convoy.box()
            self.win_hand.box()
            self.win_log.box()
            self.win_input.box()
        except curses.error:
            pass

        for w in (self.win_convoy, self.win_hand, self.win_log, self.win_input):
            try:
                w.refresh()
            except curses.error:
                pass

    def get_input(self, prompt):
        # Show the prompt in the input window (draw_screen will place it)
        # then place a small "> " and read user input on next line.
        self.draw_screen(prompt)
        curses.echo()
        try:
            # show a small prompt marker on the input line 2
            maxy, maxx = self.win_input.getmaxyx()
            # write the marker
            try:
                self.win_input.addstr(2, 1, "> ")
            except curses.error:
                pass
            self.win_input.refresh()
            # read starting after the "> " (col 3)
            input_bytes = self.win_input.getstr(2, 3, max(1, maxx - 4))
            input_str = input_bytes.decode("utf-8").strip() if input_bytes else ""
        except curses.error:
            input_str = ""
        curses.noecho()
        # redraw without the ephemeral prompt so the UI stays neat
        self.draw_screen()
        return input_str

    def build(self, player):
        if not player["hand"]:
            self.add_log("No cards in hand to build!")
            self.draw_screen()
            return False
        choice = self.get_input(f"Choose a card to build from {player['hand']}: ")
        if choice not in player["hand"]:
            self.add_log("Invalid choice!")
            self.draw_screen()
            return False
        player["hand"].remove(choice)
        player["convoy"].append(choice)
        self.convoy.append(choice)
        self.add_log(f"{player['name']} built {choice}")
        self.draw_screen()
        return True

    def drive(self, player):
        if not player["convoy"]:
            self.add_log("No cars to drive!")
            self.draw_screen()
            return False
        choice = self.get_input(f"Choose a car to drive from {player['convoy']}: ")
        if choice not in player["convoy"]:
            self.add_log("Invalid choice!")
            self.draw_screen()
            return False
        idx = self.convoy.index(choice)
        direction = self.get_input("Move forward (f) or backward (b)? ").lower()
        if direction == "f" and idx < len(self.convoy) - 1:
            self.convoy[idx], self.convoy[idx+1] = self.convoy[idx+1], self.convoy[idx]
            self.add_log(f"{player['name']} moved {choice} forward")
        elif direction == "b" and idx > 0:
            self.convoy[idx], self.convoy[idx-1] = self.convoy[idx-1], self.convoy[idx]
            self.add_log(f"{player['name']} moved {choice} backward")
        else:
            self.add_log("Can't move that way!")
            self.draw_screen()
            return False
        self.draw_screen()
        return True

    def draw(self, player):
        if not self.deck:
            self.add_log("Deck empty!")
            self.draw_screen()
            return False
        card = self.deck.pop(0)
        player["hand"].append(card)
        self.add_log(f"{player['name']} drew: {card}")
        self.draw_screen()
        return True

    def sandstorm(self):
        if not self.convoy:
            return
        destroyed = self.convoy.pop(0)
        self.junkyard.append(destroyed)
        for p in self.players:
            if destroyed in p["convoy"]:
                p["convoy"].remove(destroyed)
        self.add_log(f"Sandstorm destroyed: {destroyed}")
        self.draw_screen()

    def check_win(self):
        for i, p in enumerate(self.players):
            if not p["convoy"]:
                return 1 - i
        return None

    def take_turn(self):
        player = self.players[self.turn]
        actions = 3
        while actions > 0:
            # Show ephemeral turn message in the input window in player's color
            self.draw_screen(f"{player['name']}'s turn. Actions left: {actions}", message_color=player["color"])

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
            else:
                # unrecognized action: show a short message but don't consume action
                self.add_log(f"Unknown action: {choice}")
                self.draw_screen()

            if success:
                actions -= 1

        # sandstorm after turn
        self.sandstorm()

        winner = self.check_win()
        if winner is not None:
            self.add_log(f"{self.players[winner]['name']} wins!")
            self.draw_screen()
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
