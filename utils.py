# ─────────────────────────────────────────────
#  utils.py  –  File-handling helpers
# ─────────────────────────────────────────────
from settings import HIGHSCORE_FILE


def load_highscore() -> int:
    """Read the saved high score.  Returns 0 if file missing or corrupt."""
    try:
        with open(HIGHSCORE_FILE, "r") as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return 0


def save_highscore(score: int) -> None:
    """Persist a new high score to disk."""
    with open(HIGHSCORE_FILE, "w") as f:
        f.write(str(score))