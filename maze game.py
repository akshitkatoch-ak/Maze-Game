"""Maze 2.0: a small, dependency-free, single-player maze game."""

from collections import deque
from array import array
import math
from pathlib import Path
import random
import sys
import tempfile
import time
import tkinter as tk
import wave
from tkinter import ttk

import pygame


COLS = 24
ROWS = 18
WALLS = ("N", "E", "S", "W")
DELTAS = {
    "N": (0, -1),
    "E": (1, 0),
    "S": (0, 1),
    "W": (-1, 0),
}
OPPOSITE = {"N": "S", "E": "W", "S": "N", "W": "E"}


def generate_maze(cols, rows):
    """Return a perfect maze as cells with N/E/S/W wall flags."""
    started = time.perf_counter()
    cells = [[{wall: True for wall in WALLS} for _ in range(cols)] for _ in range(rows)]
    visited = {(0, 0)}
    stack = [(0, 0)]

    while stack:
        x, y = stack[-1]
        neighbors = []
        for wall, (dx, dy) in DELTAS.items():
            nx, ny = x + dx, y + dy
            if 0 <= nx < cols and 0 <= ny < rows and (nx, ny) not in visited:
                neighbors.append((wall, nx, ny))

        if not neighbors:
            stack.pop()
            continue

        wall, nx, ny = random.choice(neighbors)
        cells[y][x][wall] = False
        cells[ny][nx][OPPOSITE[wall]] = False
        visited.add((nx, ny))
        stack.append((nx, ny))

    elapsed_ms = (time.perf_counter() - started) * 1000
    approximate_bytes = (
        sys.getsizeof(cells)
        + sum(sys.getsizeof(row) for row in cells)
        + sum(sys.getsizeof(cell) for row in cells for cell in row)
    )
    return cells, elapsed_ms, approximate_bytes


def shortest_path(cells, start, goal):
    """Find a shortest path with BFS, returning cells and elapsed milliseconds."""
    started = time.perf_counter()
    rows, cols = len(cells), len(cells[0])
    queue = deque([start])
    previous = {start: None}

    while queue:
        x, y = queue.popleft()
        if (x, y) == goal:
            break
        for wall, (dx, dy) in DELTAS.items():
            nx, ny = x + dx, y + dy
            if (
                not cells[y][x][wall]
                and 0 <= nx < cols
                and 0 <= ny < rows
                and (nx, ny) not in previous
            ):
                previous[(nx, ny)] = (x, y)
                queue.append((nx, ny))

    path = []
    position = goal
    while position is not None:
        path.append(position)
        position = previous.get(position)
    path.reverse()
    elapsed_ms = (time.perf_counter() - started) * 1000
    return path, elapsed_ms


class GameAudio:
    """Play short game sound effects."""

    SAMPLE_RATE = 22050

    def __init__(self, fallback):
        self.fallback = fallback
        self.effects_enabled = True
        self.directory = tempfile.TemporaryDirectory(prefix="maze-audio-")
        self.ready = False
        self.effects = {}

        try:
            pygame.mixer.init(frequency=self.SAMPLE_RATE, size=-16, channels=2, buffer=256)
            self.ready = True
            pygame.mixer.set_num_channels(8)
            self._write_tone("move.wav", (660, 880), 0.12, 0.12)
            self._write_tone("win.wav", (523, 659, 784, 1047), 0.9, 0.14)
            folder = Path(self.directory.name)
            self.effects = {
                name: pygame.mixer.Sound(str(folder / f"{name}.wav"))
                for name in ("move", "win")
            }
            self.effects["move"].set_volume(0.55)
            self.effects["win"].set_volume(0.7)
        except pygame.error:
            if self.ready:
                pygame.mixer.quit()
                self.ready = False
            self.effects = {}

    @classmethod
    def _save_wave(cls, path, samples):
        with wave.open(str(path), "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(cls.SAMPLE_RATE)
            audio.writeframes(samples.tobytes())

    def _write_tone(self, filename, notes, duration, volume):
        total = int(self.SAMPLE_RATE * duration)
        segment = max(1, total // len(notes))
        samples = array("h")
        for index in range(total):
            note = min(index // segment, len(notes) - 1)
            note_time = index % segment
            envelope = min(1.0, note_time / 400, (segment - note_time) / 800)
            value = math.sin(2 * math.pi * notes[note] * note_time / self.SAMPLE_RATE)
            samples.append(int(value * envelope * volume * 32767))
        self._save_wave(Path(self.directory.name) / filename, samples)

    def play(self, effect):
        if not self.effects_enabled:
            return
        if not self.ready:
            self.fallback()
            return
        try:
            self.effects[effect].play()
        except (KeyError, pygame.error):
            self.fallback()

    def toggle_effects(self):
        self.effects_enabled = not self.effects_enabled
        return self.effects_enabled

    def close(self):
        if self.ready:
            pygame.mixer.stop()
            pygame.mixer.quit()
            self.ready = False
        self.directory.cleanup()


class MazeGame:
    def __init__(self, root):
        self.root = root
        self.root.title("Maze 2.0")
        self.root.minsize(640, 520)
        self.root.configure(bg="#f3f6fb")

        self.cells, self.generation_ms, self.memory_bytes = generate_maze(COLS, ROWS)
        self.player = (0, 0)
        self.path = []
        self.path_ms = 0.0
        self.completed = False
        self.level = 1
        self.celebration_generation = 0
        self.audio = GameAudio(self.root.bell)

        style = ttk.Style()
        style.configure("TButton", padding=(10, 6))
        style.configure("Title.TLabel", font=("Segoe UI", 20, "bold"), background="#f3f6fb")
        style.configure("Info.TLabel", font=("Segoe UI", 10), background="#f3f6fb")

        header = ttk.Frame(root, padding=(14, 10))
        header.pack(fill="x")
        ttk.Label(header, text="Maze Runner", style="Title.TLabel").pack(side="left")
        ttk.Button(header, text="New maze (R)", command=self.new_maze).pack(side="right", padx=4)
        ttk.Button(header, text="Show path (H)", command=self.toggle_path).pack(side="right", padx=4)
        self.sound_button = ttk.Button(header, text="Sound: On", command=self.toggle_sound)
        self.sound_button.pack(side="right", padx=4)

        self.canvas = tk.Canvas(root, bg="#1414B5", highlightthickness=1, highlightbackground="#d8e0ec")
        self.canvas.pack(fill="both", expand=True, padx=14, pady=(0, 8))
        self.canvas.bind("<Configure>", lambda _event: self.draw())

        self.status = ttk.Label(root, style="Info.TLabel", padding=(14, 2))
        self.status.pack(fill="x")
        self.metrics = ttk.Label(root, style="Info.TLabel", padding=(14, 2, 14, 10))
        self.metrics.pack(fill="x")

        root.bind("<KeyPress>", self.on_key)
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.focus_set()
        self.refresh_labels()
        self.draw()

    def toggle_sound(self):
        enabled = self.audio.toggle_effects()
        self.sound_button.configure(text=f"Sound: {'On' if enabled else 'Off'}")

    @property
    def goal(self):
        return COLS - 1, ROWS - 1

    def new_maze(self):
        self.celebration_generation += 1
        self.cells, self.generation_ms, self.memory_bytes = generate_maze(COLS, ROWS)
        self.player = (0, 0)
        self.path = []
        self.completed = False
        self.refresh_labels()
        self.draw()

    def toggle_path(self):
        if self.path:
            self.path = []
        else:
            self.path, self.path_ms = shortest_path(self.cells, self.player, self.goal)
        self.refresh_labels()
        self.draw()

    def on_key(self, event):
        key = event.keysym.lower()
        if key == "r":
            self.new_maze()
            return
        if key == "h":
            self.toggle_path()
            return

        controls = {
            "up": "N", "w": "N",
            "right": "E", "d": "E",
            "down": "S", "s": "S",
            "left": "W", "a": "W",
        }
        if key not in controls or self.completed:
            return

        wall = controls[key]
        x, y = self.player
        if self.cells[y][x][wall]:
            return
        dx, dy = DELTAS[wall]
        self.player = (x + dx, y + dy)
        self.path = []
        if self.player == self.goal:
            self.completed = True
            self.audio.play("win")
            self.refresh_labels()
            self.draw()
            self.start_celebration()
            return
        self.audio.play("move")
        self.refresh_labels()
        self.draw()

    def refresh_labels(self):
        if self.completed:
            message = f"Level {self.level} complete!"
        else:
            message = f"Level {self.level}  |  Move with arrow keys or W A S D. Reach the green exit!"
        self.status.configure(text=message)
        memory_kb = self.memory_bytes / 1024
        self.metrics.configure(
            text=(
                f"Generation: {self.generation_ms:.2f} ms  |  "
                f"BFS path search: {self.path_ms:.3f} ms  |  "
                f"Estimated maze storage: {memory_kb:.1f} KB  |  "
                f"Grid: {COLS} x {ROWS}"
            )
        )

    def start_celebration(self, frame=0, particles=None, generation=None):
        if generation is None:
            self.celebration_generation += 1
            generation = self.celebration_generation
        if generation != self.celebration_generation:
            return
        if frame == 0:
            colors = ("#f4c95d", "#70c1b3", "#e56b6f", "#6c8ed4", "#b48ead")
            particles = []
            width = max(self.canvas.winfo_width(), 1)
            for _ in range(70):
                x = random.randrange(width)
                y = random.randrange(-300, -5)
                color = random.choice(colors)
                item = self.canvas.create_oval(
                    x, y, x + 7, y + 10, fill=color, outline="", tags="celebration",
                )
                particles.append((item, random.uniform(-1.2, 1.2), random.uniform(3, 7)))
            self.canvas.create_rectangle(
                0, 0, width, 54, fill="#26364a", outline="", tags="celebration",
            )
            self.canvas.create_text(
                width / 2, 27, text="LEVEL COMPLETE!", fill="#ffffff",
                font=("Segoe UI", 20, "bold"), tags="celebration",
            )
        if frame >= 50:
            self.canvas.delete("celebration")
            self.level += 1
            self.new_maze()
            return
        for item, dx, dy in particles or ():
            self.canvas.move(item, dx, dy)
        self.root.after(40, self.start_celebration, frame + 1, particles, generation)

    def close(self):
        self.audio.close()
        self.root.destroy()

    def draw(self):
        if not hasattr(self, "canvas"):
            return
        self.canvas.delete("all")
        width = max(self.canvas.winfo_width(), 1)
        height = max(self.canvas.winfo_height(), 1)
        cell_size = min(width / COLS, height / ROWS)
        left = (width - cell_size * COLS) / 2
        top = (height - cell_size * ROWS) / 2

        if self.path:
            for x, y in self.path:
                x1, y1 = left + x * cell_size, top + y * cell_size
                self.canvas.create_rectangle(
                    x1 + 2, y1 + 2, x1 + cell_size - 2, y1 + cell_size - 2,
                    fill="#1bf50f", outline="",
                )

        gx, gy = self.goal
        self.canvas.create_rectangle(
            left + gx * cell_size + 3, top + gy * cell_size + 3,
            left + (gx + 1) * cell_size - 3, top + (gy + 1) * cell_size - 3,
            fill="#f1fe03", outline="",
        )

        line_color = "#ffffff"
        line_width = max(1, int(cell_size / 12))
        for y, row in enumerate(self.cells):
            for x, cell in enumerate(row):
                x1, y1 = left + x * cell_size, top + y * cell_size
                x2, y2 = x1 + cell_size, y1 + cell_size
                if cell["N"]:
                    self.canvas.create_line(x1, y1, x2, y1, fill=line_color, width=line_width)
                if cell["W"]:
                    self.canvas.create_line(x1, y1, x1, y2, fill=line_color, width=line_width)
                if cell["E"]:
                    self.canvas.create_line(x2, y1, x2, y2, fill=line_color, width=line_width)
                if cell["S"]:
                    self.canvas.create_line(x1, y2, x2, y2, fill=line_color, width=line_width)

        radius = max(4, cell_size * 0.29)
        x, y = self.player
        cx = left + (x + 0.5) * cell_size
        cy = top + (y + 0.5) * cell_size
        self.canvas.create_oval(
            cx - radius, cy - radius, cx + radius, cy + radius,
            fill="#e05252", outline="#ffffff", width=2,
        )


def main():
    root = tk.Tk()
    MazeGame(root)
    root.mainloop()


if __name__ == "__main__":
    main()
