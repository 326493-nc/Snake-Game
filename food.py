# ─────────────────────────────────────────────
#  food.py  –  Food entity
# ─────────────────────────────────────────────
import random
from settings import COLS, ROWS


class Food:
    """Spawns food on a random unoccupied cell."""

    def __init__(self, occupied: list[tuple[int, int]]):
        self.position = self._random_pos(occupied)
        self._bob_tick = 0      # for animated bobbing

    def respawn(self, occupied: list[tuple[int, int]]) -> None:
        self.position = self._random_pos(occupied)
        self._bob_tick = 0

    def _random_pos(self, occupied: list[tuple[int, int]]) -> tuple[int, int]:
        all_cells = {(c, r) for c in range(COLS) for r in range(ROWS)}
        free = list(all_cells - set(occupied))
        return random.choice(free) if free else (0, 0)

    def bob_offset(self) -> float:
        """Returns a y-pixel offset for a smooth floating animation."""
        import math
        self._bob_tick += 1
        return math.sin(self._bob_tick * 0.08) * 3