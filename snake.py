# ─────────────────────────────────────────────
#  snake.py  –  Snake entity
# ─────────────────────────────────────────────
from settings import COLS, ROWS


class Snake:
    """Manages the snake body, movement, and collision."""

    def __init__(self):
        mx, my = COLS // 2, ROWS // 2
        # body is a list of (col, row) tuples, head first
        self.body = [(mx, my), (mx - 1, my), (mx - 2, my)]
        self.direction = (1, 0)   # moving right
        self.next_dir  = (1, 0)
        self.grew      = False    # set True for one tick after eating

    # ── direction input ──────────────────────────────────────
    def change_direction(self, new_dir: tuple[int, int]) -> None:
        """Prevent 180° reversal."""
        dx, dy = new_dir
        cx, cy = self.direction
        if (dx, dy) != (-cx, -cy):
            self.next_dir = (dx, dy)

    # ── move one step ────────────────────────────────────────
    def move(self) -> None:
        self.direction = self.next_dir
        hx, hy = self.body[0]
        dx, dy = self.direction
        new_head = (hx + dx, hy + dy)
        self.body.insert(0, new_head)
        if not self.grew:
            self.body.pop()
        self.grew = False

    def grow(self) -> None:
        """Call after eating; next move() keeps the tail."""
        self.grew = True

    # ── collision checks ─────────────────────────────────────
    def hit_wall(self) -> bool:
        hx, hy = self.body[0]
        return not (0 <= hx < COLS and 0 <= hy < ROWS)

    def hit_self(self) -> bool:
        return self.body[0] in self.body[1:]

    @property
    def head(self) -> tuple[int, int]:
        return self.body[0]

    def __len__(self) -> int:
        return len(self.body)