# ╔═══════════════════════════════════════════════════════════════════╗
# ║  Copyright (c) 2026  Christo Joseph  –  All rights reserved       ║
# ║  BTEC L3 Extended Diploma in IT  |  Slough and Langley College    ║
# ║  Unauthorised copying or modification is strictly prohibited.     ║
# ╚═══════════════════════════════════════════════════════════════════╝
#
# settings.py  –  Global constants

# Window
TITLE        = "SNAKE  •  2025 Edition"
SCREEN_W     = 660
SCREEN_H     = 660
FPS          = 60

# Grid
CELL         = 24          # pixels per grid cell
COLS         = 25
ROWS         = 25
GRID_W       = COLS * CELL  # 600 px
GRID_H       = ROWS * CELL  # 600 px
GRID_OFFSET_X = (SCREEN_W - GRID_W) // 2
GRID_OFFSET_Y = (SCREEN_H - GRID_H) // 2

# Colours  (R, G, B)
C_BG          = (10,  14,  26)
C_GRID        = (18,  24,  40)
C_SNAKE_HEAD  = (57, 255,  20)
C_SNAKE_BODY  = (0,  180,  50)
C_SNAKE_TAIL  = (0,  100,  30)
C_FOOD        = (255,  60,  60)
C_FOOD_SHINE  = (255, 150, 150)
C_WHITE       = (230, 240, 255)
C_MUTED       = ( 80,  90, 110)
C_GOLD        = (255, 215,   0)
C_CYAN        = (  0, 220, 255)
C_RED         = (255,  60,  60)
C_GREEN       = ( 57, 255,  20)
C_PAUSE       = (  0, 180, 255)

# Difficulty  →  (ms between game ticks, points per food)
DIFFICULTIES = {
    "Easy":   (180, 10),
    "Medium": (110, 20),
    "Hard":   ( 65, 30),
}

WIN_LENGTH = COLS * ROWS - 10   # board almost full  →  you win

HIGHSCORE_FILE = "highscore.txt"