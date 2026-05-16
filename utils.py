# ╔═══════════════════════════════════════════════════════════════════╗
# ║  Copyright (c) 2026  Christo Joseph  –  All rights reserved       ║
# ║  BTEC L3 Extended Diploma in IT  |  Slough and Langley College    ║
# ║  Unauthorised copying or modification is strictly prohibited.     ║
# ╚═══════════════════════════════════════════════════════════════════╝
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