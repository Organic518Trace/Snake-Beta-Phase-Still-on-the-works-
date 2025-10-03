"""
Simple Snake game using Tkinter.

Features:
- Arrow key controls (Up, Down, Left, Right) and WASD
- Points system (each food eaten gives +10 points)
- Stopwatch (time since game start or since last restart)
- Pause/Resume (Space)
- Restart (R)
- Simulated microtransaction offers every 60 seconds of in-game time

Run: python snake.py

Tested on Python 3.8+ with Tkinter available.
"""

import tkinter as tk
import random
import time


CELL_SIZE = 20
GRID_WIDTH = 30
GRID_HEIGHT = 20
GAME_SPEED = 100  # base milliseconds between moves (lower is faster)


class SnakeGame(tk.Canvas):
    def __init__(self, master):
        width = CELL_SIZE * GRID_WIDTH
        height = CELL_SIZE * GRID_HEIGHT
        super().__init__(master, width=width, height=height, bg="black")

        self.master = master
        self.pack()

        # Game state
        self.reset_state()

        # Score and timer labels
        self.score_var = tk.StringVar(value="Score: 0")
        self.time_var = tk.StringVar(value="Time: 00:00")
        self.effects_var = tk.StringVar(value="")

        self.info_frame = tk.Frame(master)
        self.info_frame.pack(fill=tk.X)
        tk.Label(self.info_frame, textvariable=self.score_var, font=("Consolas", 12)).pack(side=tk.LEFT, padx=8)
        tk.Label(self.info_frame, textvariable=self.effects_var, font=("Consolas", 10)).pack(side=tk.LEFT, padx=8)
        tk.Label(self.info_frame, textvariable=self.time_var, font=("Consolas", 12)).pack(side=tk.RIGHT, padx=8)

        # Controls
        master.bind('<Key>', self.on_key)

        # Microtransaction state (initialize before starting stopwatch)
        self._microtxn_job = None
        self.microtxn_interval = 60.0  # seconds between offers (game time)
        self.microtxn_shown_at = None
        self._microtxn_overlay_win = None
        self._microtxn_overlay_frame = None
        self.speed_boost_until = None
        self.shield_until = None

        # move timing state
        self.current_speed = GAME_SPEED
        self._move_job = None

        # Start the stopwatch updater
        self._stopwatch_job = None
        self.update_stopwatch()

        # Kick off game loop
        self.schedule_move()

    def reset_state(self):
        self.direction = 'Right'  # initial direction
        mid_x = GRID_WIDTH // 2
        mid_y = GRID_HEIGHT // 2
        self.snake = [(mid_x - i, mid_y) for i in range(3)]  # list of (x,y) tuples
        self.snake_ids = []
        self.food = None
        self.food_id = None
        self.score = 0
        self.game_over = False
        self.paused = False
        self.start_time = None
        self.elapsed_before_pause = 0.0

        self.delete('all')
        self.place_food()
        self.draw_snake()

    def place_food(self):
        positions = set(self.snake)
        while True:
            fx = random.randrange(GRID_WIDTH)
            fy = random.randrange(GRID_HEIGHT)
            if (fx, fy) not in positions:
                self.food = (fx, fy)
                break
        if self.food_id:
            self.delete(self.food_id)
        x1, y1, x2, y2 = self.cell_to_coords(self.food[0], self.food[1])
        self.food_id = self.create_rectangle(x1, y1, x2, y2, fill='red', outline='yellow')

    def draw_snake(self):
        # remove old ids
        for _id in self.snake_ids:
            self.delete(_id)
        self.snake_ids = []
        for i, (x, y) in enumerate(self.snake):
            x1, y1, x2, y2 = self.cell_to_coords(x, y)
            color = 'green' if i == 0 else 'lightgreen'
            _id = self.create_rectangle(x1, y1, x2, y2, fill=color, outline='black')
            self.snake_ids.append(_id)

    def cell_to_coords(self, x, y):
        x1 = x * CELL_SIZE
        y1 = y * CELL_SIZE
        x2 = x1 + CELL_SIZE
        y2 = y1 + CELL_SIZE
        return x1, y1, x2, y2

    def on_key(self, event):
        key = event.keysym
        # support WASD and arrows
        mapping = {
            'w': 'Up', 'W': 'Up',
            's': 'Down', 'S': 'Down',
            'a': 'Left', 'A': 'Left',
            'd': 'Right', 'D': 'Right',
            'Up': 'Up', 'Down': 'Down', 'Left': 'Left', 'Right': 'Right'
        }
        if key in mapping:
            new_dir = mapping[key]
            opposite = {'Up': 'Down', 'Down': 'Up', 'Left': 'Right', 'Right': 'Left'}
            if opposite[new_dir] != self.direction:
                self.direction = new_dir
                if self.start_time is None:
                    self.start_time = time.monotonic()
        elif key in ('space', 'spacebar') or key == 'space':
            self.toggle_pause()
        elif key in ('r', 'R'):
            self.restart()

    def toggle_pause(self):
        if self.game_over:
            return
        if not self.paused:
            # pause
            self.paused = True
            if self._stopwatch_job:
                self.after_cancel(self._stopwatch_job)
                self._stopwatch_job = None
            if self._move_job:
                self.after_cancel(self._move_job)
                self._move_job = None
            if self.start_time is not None:
                self.elapsed_before_pause += time.monotonic() - self.start_time
                self.start_time = None
        else:
            # resume
            self.paused = False
            if self.start_time is None:
                self.start_time = time.monotonic()
            self.update_stopwatch()
            self.schedule_move()

    def restart(self):
        # cancel scheduled jobs
        if self._stopwatch_job:
            self.after_cancel(self._stopwatch_job)
            self._stopwatch_job = None
        if self._move_job:
            self.after_cancel(self._move_job)
            self._move_job = None

        self.reset_state()
        self.score_var.set(f"Score: {self.score}")
        self.time_var.set("Time: 00:00")
        self.start_time = time.monotonic()
        self.elapsed_before_pause = 0.0
        self.paused = False
        self.current_speed = GAME_SPEED
        self.speed_boost_until = None
        self.shield_until = None
        # reset microtransaction schedule so offers come microtxn_interval after restart
        self.microtxn_shown_at = self.microtxn_interval
        self.effects_var.set("")
        self.update_stopwatch()
        self.schedule_move()

    def update_stopwatch(self):
        # update time display based on in-game elapsed time
        elapsed = self.elapsed_before_pause
        if self.start_time is not None:
            elapsed += time.monotonic() - self.start_time
        mins = int(elapsed // 60)
        secs = int(elapsed % 60)
        self.time_var.set(f"Time: {mins:02d}:{secs:02d}")

        # schedule next stopwatch update
        if not self.paused and not self.game_over:
            self._stopwatch_job = self.after(250, self.update_stopwatch)

        # schedule microtransaction offers based on game elapsed time
        self.maybe_schedule_microtxn()

        # update active effects and UI
        self.update_effects_state()

    def update_effects_state(self):
        now = time.monotonic()
        parts = []
        # handle speed boost expiry
        if self.speed_boost_until and now >= self.speed_boost_until:
            self.speed_boost_until = None
            self.current_speed = GAME_SPEED
        if self.speed_boost_until:
            parts.append('Speed+')

        # handle shield expiry
        if self.shield_until and now >= self.shield_until:
            self.shield_until = None
        if self.shield_until:
            parts.append('Shield')

        self.effects_var.set(' | '.join(parts))

    def schedule_move(self):
        # schedule the next move using current_speed
        if self._move_job:
            self.after_cancel(self._move_job)
            self._move_job = None
        if not self.paused and not self.game_over:
            self._move_job = self.after(int(self.current_speed), self._do_move)

    def _do_move(self):
        # adjust speed if speed boost is active
        now = time.monotonic()
        if self.speed_boost_until and now < self.speed_boost_until:
            self.current_speed = max(20, int(GAME_SPEED * 0.5))  # faster (lower interval)
        else:
            self.current_speed = GAME_SPEED

        self.move_snake()
        self.draw_snake()
        self.schedule_move()

    def maybe_schedule_microtxn(self):
        """Show a microtransaction popup every microtxn_interval seconds of active game time.
        This uses the in-game elapsed time (not wall-clock) so pausing stops the timer.
        """
        if self.game_over:
            return
        # determine elapsed game time
        elapsed = self.elapsed_before_pause
        if self.start_time is not None:
            elapsed += time.monotonic() - self.start_time

        # decide when to show first offer
        if self.microtxn_shown_at is None:
            # schedule first at microtxn_interval
            self.microtxn_shown_at = self.microtxn_interval

        # show when elapsed crosses the next threshold
        if elapsed >= self.microtxn_shown_at:
            # ensure we don't spam multiple times in one update
            self.microtxn_shown_at += self.microtxn_interval
            self.show_microtransaction_offer()

    def show_microtransaction_offer(self):
        """Pause game and show an in-canvas overlay offering fake microtransactions.
        Selecting an offer applies it, closes the overlay and unpauses (unless the game was already paused).
        """
        # avoid showing multiple overlays
        if self._microtxn_overlay_win is not None:
            return

        # record whether the game was already paused so we restore correctly
        was_paused = self.paused
        if not was_paused:
            # pause the game
            self.toggle_pause()

        # build overlay frame
        frame = tk.Frame(self, bg='black', bd=2, relief=tk.RIDGE)
        lbl = tk.Label(frame, text='Special Offers', font=("Consolas", 12), fg='white', bg='black')
        lbl.pack(padx=10, pady=(8, 4))

        info = tk.Label(frame, text='Spend points to buy effects:', font=("Consolas", 10), fg='white', bg='black')
        info.pack(padx=10, pady=(0, 8))

        offers = [
            ('Grow +2', 20, lambda: self.apply_grow(2)),
            ('Speed boost (10s)', 30, lambda: self.apply_speed_boost(10)),
            ('Shield (10s)', 25, lambda: self.apply_shield(10)),
        ]

        for name, cost, action in offers:
            row = tk.Frame(frame, bg='black')
            row.pack(fill=tk.X, padx=8, pady=4)
            lbl = tk.Label(row, text=f"{name} — {cost} pts", font=("Consolas", 10), fg='white', bg='black')
            lbl.pack(side=tk.LEFT)

            def make_buy(act=action, c=cost):
                if self.score >= c:
                    self.score -= c
                    self.score_var.set(f"Score: {self.score}")
                    act()
                    self.close_microtxn_overlay(was_paused)
                else:
                    # flash label to indicate insufficient funds
                    old = lbl.cget('fg')
                    lbl.config(fg='red')
                    lbl.after(700, lambda: lbl.config(fg=old))

            btn = tk.Button(row, text='Buy', command=make_buy)
            btn.pack(side=tk.RIGHT)

        # close button
        btn_close = tk.Button(frame, text='Close', command=lambda: self.close_microtxn_overlay(was_paused))
        btn_close.pack(pady=(6, 8))

        # place frame centered on canvas
        w = CELL_SIZE * GRID_WIDTH
        h = CELL_SIZE * GRID_HEIGHT
        win_id = self.create_window(w//2, h//2, window=frame)
        self._microtxn_overlay_win = win_id
        self._microtxn_overlay_frame = frame

        # auto-close after 12 seconds (if still present)
        def auto_close():
            if self._microtxn_overlay_win is not None:
                self.close_microtxn_overlay(was_paused)

        self.after(12000, auto_close)

    def close_microtxn_overlay(self, was_paused):
        # destroy overlay and restore paused state
        if self._microtxn_overlay_win is not None:
            try:
                self.delete(self._microtxn_overlay_win)
            except Exception:
                pass
            # destroy the frame widget to free resources
            try:
                self._microtxn_overlay_frame.destroy()
            except Exception:
                pass
            self._microtxn_overlay_win = None
            self._microtxn_overlay_frame = None

        # if the game was not paused before the overlay, unpause now
        if not was_paused and not self.game_over:
            self.toggle_pause()


    def apply_grow(self, n):
        # add n segments to tail by appending copies of the last segment
        if self.snake:
            for _ in range(n):
                self.snake.append(self.snake[-1])


    def apply_speed_boost(self, seconds):
        # temporarily reduce GAME_SPEED (increase actual speed)
        # implement by setting a per-game variable and scheduling end
        now = time.monotonic()
        self.speed_boost_until = now + seconds
        # apply immediate effect by lowering after delay interval
        # We'll use GAME_SPEED_FACTOR in move timing checks


    def apply_shield(self, seconds):
        now = time.monotonic()
        self.shield_until = now + seconds


    def game_loop(self):
        if not self.paused and not self.game_over:
            self.move_snake()
            self.draw_snake()
        self.after(GAME_SPEED, self.game_loop)

    def move_snake(self):
        head_x, head_y = self.snake[0]
        move_map = {'Up': (0, -1), 'Down': (0, 1), 'Left': (-1, 0), 'Right': (1, 0)}
        dx, dy = move_map.get(self.direction, (1, 0))
        new_head = ((head_x + dx) % GRID_WIDTH, (head_y + dy) % GRID_HEIGHT)

        # collision with self
        now = time.monotonic()
        shield_active = self.shield_until and now < self.shield_until
        if new_head in self.snake:
            if not shield_active:
                self.end_game()
                return

        self.snake.insert(0, new_head)

        # check food
        if new_head == self.food:
            self.score += 10
            self.score_var.set(f"Score: {self.score}")
            self.place_food()
        else:
            # remove tail
            self.snake.pop()

        # start timer if it's the first move
        if self.start_time is None:
            self.start_time = time.monotonic()

    def end_game(self):
        self.game_over = True
        self.paused = True
        # show game over text
        w = CELL_SIZE * GRID_WIDTH
        h = CELL_SIZE * GRID_HEIGHT
        self.create_rectangle(w//4, h//3, w*3//4, h*2//3, fill='black', outline='white')
        self.create_text(w//2, h//2 - 10, text='GAME OVER', fill='white', font=("Consolas", 24, 'bold'))
        self.create_text(w//2, h//2 + 20, text=f'Score: {self.score}', fill='white', font=("Consolas", 14))
        self.create_text(w//2, h//2 + 46, text='Press R to restart', fill='white', font=("Consolas", 12))

    def run(self):
        self.master.mainloop()


def main():
    root = tk.Tk()
    root.title('Snake')
    # make window not resizable to keep grid consistent
    root.resizable(False, False)

    game = SnakeGame(root)

    # Instructions label
    instr = tk.Label(root, text='Arrows: move • Space: pause/resume • R: restart', font=("Consolas", 10))
    instr.pack(pady=6)

    game.run()


if __name__ == '__main__':
    main()
