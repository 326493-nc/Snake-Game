# ╔══════════════════════════════════════════════════════════════╗
# ║           SNAKE GAME  –  2025 Edition                        ║
# ║                                                              ║
# ║  Copyright (c) 2025  [YOUR FULL NAME]                        ║
# ║  All rights reserved.                                        ║
# ║                                                              ║
# ║  Created for:  BTEC Level 3 Computer Science /               ║
# ║                Games Development Assignment                  ║
# ║  Institution:  [YOUR COLLEGE NAME]                           ║
# ║  Student ID:   [YOUR STUDENT ID]                             ║
# ║                                                              ║
# ║  LICENCE NOTICE                                              ║
# ║  This source code is the original work of the author above.  ║
# ║  Unauthorised copying, modification, redistribution or use   ║
# ║  of this file, in whole or in part, is strictly prohibited   ║
# ║  without the express written permission of the author.       ║
# ║                                                              ║
# ║  This project was submitted as academic coursework.          ║
# ║  Any reproduction without attribution constitutes            ║
# ║  academic plagiarism and may be subject to disciplinary       ║
# ║  action by the institution.                                  ║
# ╚══════════════════════════════════════════════════════════════╝
#
#  game.py  –  Game loop, states, rendering, UI
#  v2  –  Smooth interpolated movement (no jumps)
# ─────────────────────────────────────────────
import pygame, sys, math, random
from settings import *
from snake  import Snake
from food   import Food
from utils  import load_highscore, save_highscore


# ══════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════
# ── Copyright string (rendered in-game) ──────
COPYRIGHT = "\u00a9 2026 Christo Joseph  |  All rights reserved  |  BTEC Level 3 Assignment"


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t

def lerp_colour(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


# ══════════════════════════════════════════════
#  Particle
# ══════════════════════════════════════════════
class Particle:
    def __init__(self, x, y, colour):
        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(1.5, 5.0)
        self.x, self.y = float(x), float(y)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life   = 1.0
        self.colour = colour
        self.radius = random.randint(2, 5)

    def update(self, dt: float):
        self.x  += self.vx * dt * 60
        self.y  += self.vy * dt * 60
        self.vy += 0.15 * dt * 60
        self.life -= 0.035 * dt * 60

    def draw(self, surface):
        if self.life <= 0:
            return
        alpha = int(max(0, min(255, self.life * 255)))
        s = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.colour, alpha),
                           (self.radius, self.radius), self.radius)
        surface.blit(s, (int(self.x - self.radius), int(self.y - self.radius)))


# ══════════════════════════════════════════════
#  FloatText  (+pts label above food)
# ══════════════════════════════════════════════
class FloatText:
    def __init__(self, text, x, y, colour, font):
        self.surf  = font.render(text, True, colour)
        self.x, self.y = float(x), float(y)
        self.life  = 1.0
        self.vy    = -1.8

    def update(self, dt: float):
        self.y    += self.vy * dt * 60
        self.life -= 0.03  * dt * 60

    def draw(self, surface):
        if self.life <= 0:
            return
        alpha = int(max(0, min(255, self.life * 255)))
        s = self.surf.copy()
        s.set_alpha(alpha)
        surface.blit(s, (int(self.x) - s.get_width() // 2, int(self.y)))


# ══════════════════════════════════════════════
#  SmoothSegment  – tracks visual pixel position
# ══════════════════════════════════════════════
class SmoothSegment:
    """
    Stores the PREVIOUS and CURRENT grid cell of one snake segment.
    The renderer interpolates between them every frame, so motion is
    pixel-perfect smooth instead of jumping one full cell per tick.
    """
    def __init__(self, col: int, row: int):
        self.prev_col = col;  self.prev_row = row
        self.curr_col = col;  self.curr_row = row

    def pixel_pos(self, t: float) -> tuple[float, float]:
        """Interpolated pixel top-left at fraction t in [0, 1]."""
        px = lerp(self.prev_col, self.curr_col, t) * CELL + GRID_OFFSET_X
        py = lerp(self.prev_row, self.curr_row, t) * CELL + GRID_OFFSET_Y
        return px, py


# ══════════════════════════════════════════════
#  Game
# ══════════════════════════════════════════════
class Game:
    SPLASH   = "splash"
    MENU     = "menu"
    PLAYING  = "playing"
    PAUSED   = "paused"
    GAMEOVER = "gameover"
    WIN      = "win"

    SPLASH_DURATION = 3500   # milliseconds to show copyright screen

    def __init__(self):
        pygame.init()
        pygame.display.set_caption(TITLE)
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self.clock  = pygame.time.Clock()

        # reusable surfaces (avoid re-allocating every frame)
        self._overlay_surf = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        self._flash_surf   = pygame.Surface((SCREEN_W, SCREEN_H))
        self._flash_surf.fill((57, 255, 20))

        # fonts
        self.font_xl = pygame.font.SysFont("consolas", 62, bold=True)
        self.font_lg = pygame.font.SysFont("consolas", 38, bold=True)
        self.font_md = pygame.font.SysFont("consolas", 22, bold=True)
        self.font_sm = pygame.font.SysFont("consolas", 16)
        self.font_xs = pygame.font.SysFont("consolas", 13)

        self.highscore  = load_highscore()
        self.state      = self.SPLASH          # ← start on splash screen
        self._splash_start = pygame.time.get_ticks()
        self.difficulty = "Medium"

        # game objects
        self.snake      = None
        self.food       = None
        self.score      = 0
        self.food_eaten = 0

        # ── smooth movement ──────────────────
        # one SmoothSegment per snake body cell
        self._segments  : list[SmoothSegment] = []
        # fraction through current tick  [0 = just ticked, 1 = ready for next]
        self._interp_t  = 0.0
        self._tick_ms   = 150     # ms between logic ticks
        self._last_tick = 0       # get_ticks() at last tick

        # visual effects
        self.particles  : list[Particle]  = []
        self.floats     : list[FloatText] = []
        self.flash_alpha  = 0
        self.death_shake  = 0
        self.shake_offset = (0, 0)
        self.grid_pulse   = 0.0
        self.win_burst_done = False

        # menu
        self._menu_hover = None
        self._menu_rects : dict = {}

    # ─────────────────────────────────────────
    #  Difficulty helpers
    # ─────────────────────────────────────────
    def _points_per_food(self):
        return DIFFICULTIES[self.difficulty][1]

    # ─────────────────────────────────────────
    #  Game lifecycle
    # ─────────────────────────────────────────
    def new_game(self):
        self.snake      = Snake()
        self.food       = Food(self.snake.body)
        self.score      = 0
        self.food_eaten = 0
        self.particles.clear()
        self.floats.clear()
        self.flash_alpha    = 0
        self.death_shake    = 0
        self.win_burst_done = False

        self._tick_ms, _ = DIFFICULTIES[self.difficulty]
        self._last_tick  = pygame.time.get_ticks()
        self._interp_t   = 0.0

        # build one SmoothSegment per initial body cell
        self._segments = [SmoothSegment(c, r) for c, r in self.snake.body]

        self.state = self.PLAYING

    # ─────────────────────────────────────────
    #  Main loop
    # ─────────────────────────────────────────
    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0   # seconds since last frame
            # auto-advance splash after SPLASH_DURATION ms
            if self.state == self.SPLASH:
                elapsed = pygame.time.get_ticks() - self._splash_start
                if elapsed >= self.SPLASH_DURATION:
                    self.state = self.MENU
            self._handle_events()
            self._update(dt)
            self._draw()

    # ─────────────────────────────────────────
    #  Events
    # ─────────────────────────────────────────
    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._quit()
            if event.type == pygame.KEYDOWN:
                self._on_key(event.key)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._on_click(event.pos)

        if self.state == self.MENU:
            self._menu_hover = self._hovered_button(pygame.mouse.get_pos())

    def _on_key(self, key):
        s = self.state
        # any key skips the splash screen
        if s == self.SPLASH:
            self.state = self.MENU
            return
        if s == self.PLAYING:
            if   key == pygame.K_UP:    self.snake.change_direction((0, -1))
            elif key == pygame.K_DOWN:  self.snake.change_direction((0,  1))
            elif key == pygame.K_LEFT:  self.snake.change_direction((-1, 0))
            elif key == pygame.K_RIGHT: self.snake.change_direction(( 1, 0))
            elif key in (pygame.K_ESCAPE, pygame.K_p):
                self.state = self.PAUSED
        elif s == self.PAUSED:
            if key in (pygame.K_ESCAPE, pygame.K_c, pygame.K_p):
                # adjust _last_tick so interpolation continues cleanly
                self._last_tick = pygame.time.get_ticks() - int(self._interp_t * self._tick_ms)
                self.state = self.PLAYING
            elif key == pygame.K_r: self.new_game()
            elif key == pygame.K_m: self.state = self.MENU
        elif s == self.GAMEOVER:
            if key == pygame.K_r: self.new_game()
            elif key == pygame.K_m: self.state = self.MENU
        elif s == self.WIN:
            if key == pygame.K_r: self.new_game()
            elif key == pygame.K_m: self.state = self.MENU

    def _on_click(self, pos):
        # clicking anywhere skips the splash
        if self.state == self.SPLASH:
            self.state = self.MENU
            return
        if self.state == self.MENU:
            btn = self._hovered_button(pos)
            if btn in DIFFICULTIES:
                self.difficulty = btn
                self.new_game()

    # ─────────────────────────────────────────
    #  Logic tick (runs at game speed, not FPS)
    # ─────────────────────────────────────────
    def _try_tick(self):
        """Fire a game-logic tick if enough wall-clock time has passed."""
        now = pygame.time.get_ticks()
        if now - self._last_tick >= self._tick_ms:
            self._last_tick += self._tick_ms   # fixed step; prevents drift
            self._interp_t   = 0.0
            self._game_tick()

    def _game_tick(self):
        # snapshot current grid positions into 'prev' before moving
        for seg, (c, r) in zip(self._segments, self.snake.body):
            seg.prev_col, seg.prev_row = c, r

        self.snake.move()

        if self.snake.hit_wall() or self.snake.hit_self():
            self._trigger_death()
            return

        body = self.snake.body

        # grow segment list if snake just ate
        while len(self._segments) < len(body):
            last = self._segments[-1]
            self._segments.append(SmoothSegment(last.curr_col, last.curr_row))
        self._segments = self._segments[:len(body)]

        # commit new grid positions into 'curr'
        for seg, (c, r) in zip(self._segments, body):
            seg.curr_col, seg.curr_row = c, r

        if self.snake.head == self.food.position:
            self._eat_food()
            if len(self.snake) >= WIN_LENGTH:
                self._trigger_win()

    def _eat_food(self):
        pts = self._points_per_food()
        self.score      += pts
        self.food_eaten += 1
        if self.score > self.highscore:
            self.highscore = self.score
            save_highscore(self.highscore)

        fx = GRID_OFFSET_X + self.food.position[0] * CELL + CELL // 2
        fy = GRID_OFFSET_Y + self.food.position[1] * CELL + CELL // 2
        for _ in range(14):
            self.particles.append(
                Particle(fx, fy, random.choice([C_GREEN, C_GOLD, C_CYAN, C_FOOD])))
        self.floats.append(FloatText(f"+{pts}", fx, fy - 10, C_GOLD, self.font_md))
        self.flash_alpha = 55

        self.snake.grow()
        self.food.respawn(self.snake.body)

    def _trigger_death(self):
        self.state       = self.GAMEOVER
        self.death_shake = 22
        hx = GRID_OFFSET_X + self.snake.head[0] * CELL + CELL // 2
        hy = GRID_OFFSET_Y + self.snake.head[1] * CELL + CELL // 2
        for _ in range(35):
            self.particles.append(Particle(hx, hy, random.choice([C_RED, (255,140,0)])))

    def _trigger_win(self):
        self.state = self.WIN

    # ─────────────────────────────────────────
    #  Per-frame update (60 fps)
    # ─────────────────────────────────────────
    def _update(self, dt: float):
        self.grid_pulse = (self.grid_pulse + 0.04) % (math.pi * 2)

        for p in self.particles: p.update(dt)
        self.particles = [p for p in self.particles if p.life > 0]
        for f in self.floats:    f.update(dt)
        self.floats = [f for f in self.floats if f.life > 0]

        if self.flash_alpha > 0:
            self.flash_alpha = max(0, self.flash_alpha - 4)

        if self.death_shake > 0:
            self.death_shake -= 1
            mag = self.death_shake * 0.7
            self.shake_offset = (random.randint(-int(mag), int(mag)),
                                 random.randint(-int(mag), int(mag)))
        else:
            self.shake_offset = (0, 0)

        if self.state == self.WIN and not self.win_burst_done:
            self.win_burst_done = True
            for _ in range(80):
                x = random.randint(GRID_OFFSET_X, GRID_OFFSET_X + GRID_W)
                y = random.randint(GRID_OFFSET_Y, GRID_OFFSET_Y + GRID_H)
                self.particles.append(
                    Particle(x, y, random.choice([C_GREEN, C_GOLD, C_CYAN, (255,100,200)])))

        # advance interpolation fraction
        if self.state == self.PLAYING:
            self._try_tick()
            elapsed = pygame.time.get_ticks() - self._last_tick
            self._interp_t = min(1.0, elapsed / self._tick_ms)

    # ══════════════════════════════════════════
    #  DRAWING
    # ══════════════════════════════════════════
    def _draw(self):
        ox, oy = self.shake_offset
        self.screen.fill(C_BG)
        self._draw_grid(ox, oy)

        if self.state not in (self.SPLASH, self.MENU):
            self._draw_food(ox, oy)
            seg_alpha = 100 if self.state in (self.GAMEOVER, self.WIN) else 255
            self._draw_snake(ox, oy, seg_alpha)

        for p in self.particles: p.draw(self.screen)
        for f in self.floats:    f.draw(self.screen)

        if self.flash_alpha > 0:
            self._flash_surf.set_alpha(self.flash_alpha)
            self.screen.blit(self._flash_surf, (0, 0))

        if self.state in (self.PLAYING, self.PAUSED, self.GAMEOVER, self.WIN):
            self._draw_hud()

        if   self.state == self.SPLASH:    self._draw_splash()
        elif self.state == self.MENU:      self._draw_menu()
        elif self.state == self.PAUSED:    self._draw_popup_paused()
        elif self.state == self.GAMEOVER:  self._draw_popup_gameover()
        elif self.state == self.WIN:       self._draw_popup_win()

        pygame.display.flip()

    # ── grid ──────────────────────────────────
    def _draw_grid(self, ox=0, oy=0):
        v   = int(8 + math.sin(self.grid_pulse) * 4)
        col = (30 + v, 50 + v, 80 + v)
        for c in range(COLS + 1):
            x = GRID_OFFSET_X + c * CELL + ox
            pygame.draw.line(self.screen, col,
                             (x, GRID_OFFSET_Y + oy),
                             (x, GRID_OFFSET_Y + GRID_H + oy))
        for r in range(ROWS + 1):
            y = GRID_OFFSET_Y + r * CELL + oy
            pygame.draw.line(self.screen, col,
                             (GRID_OFFSET_X + ox, y),
                             (GRID_OFFSET_X + GRID_W + ox, y))
        pygame.draw.rect(self.screen, (40, 60, 90),
                         (GRID_OFFSET_X + ox - 1, GRID_OFFSET_Y + oy - 1,
                          GRID_W + 2, GRID_H + 2), 2)

    # ── snake (interpolated) ──────────────────
    def _draw_snake(self, ox=0, oy=0, alpha=255):
        t = self._interp_t   # 0 → just moved,  1 → about to move again
        n = len(self._segments)

        for i, seg in enumerate(self._segments):
            frac = 1 - i / n
            col  = lerp_colour(C_SNAKE_TAIL, C_SNAKE_HEAD, frac)
            if i == 0:
                col = C_SNAKE_HEAD

            # smooth pixel position
            px, py = seg.pixel_pos(t)
            px += ox;  py += oy

            pad = 2 if i == 0 else 3
            sz  = CELL - pad * 2
            sx  = int(px) + pad
            sy  = int(py) + pad
            rad = 5 if i == 0 else 3

            # head glow
            if i == 0:
                gs = pygame.Surface((sz + 10, sz + 10), pygame.SRCALPHA)
                pygame.draw.rect(gs, (*C_SNAKE_HEAD, 35),
                                 (0, 0, sz + 10, sz + 10), border_radius=rad + 4)
                self.screen.blit(gs, (sx - 5, sy - 5))

            # segment rectangle
            s = pygame.Surface((sz, sz), pygame.SRCALPHA)
            pygame.draw.rect(s, (*col, alpha), (0, 0, sz, sz), border_radius=rad)
            self.screen.blit(s, (sx, sy))

            if i == 0:
                self._draw_eyes_at(sx + sz // 2, sy + sz // 2)

    def _draw_eyes_at(self, cx, cy):
        dx, dy = self.snake.direction
        offsets = {
            ( 1,  0): [( 3,-4),( 3, 4)],
            (-1,  0): [(-3,-4),(-3, 4)],
            ( 0, -1): [(-4,-3),( 4,-3)],
            ( 0,  1): [(-4, 3),( 4, 3)],
        }
        for ex, ey in offsets.get((dx, dy), [(3,-4),(3,4)]):
            pygame.draw.circle(self.screen, (5, 10, 20),  (cx+ex, cy+ey), 3)
            pygame.draw.circle(self.screen, C_SNAKE_HEAD, (cx+ex-1, cy+ey-1), 1)

    # ── food ──────────────────────────────────
    def _draw_food(self, ox=0, oy=0):
        fc, fr = self.food.position
        bob = self.food.bob_offset()
        cx  = GRID_OFFSET_X + fc * CELL + CELL // 2 + ox
        cy  = int(GRID_OFFSET_Y + fr * CELL + CELL // 2 + bob) + oy
        r   = CELL // 2 - 3

        aura = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
        pygame.draw.circle(aura, (*C_FOOD, 45), (r*2, r*2), r*2)
        self.screen.blit(aura, (cx - r*2, cy - r*2))

        pygame.draw.circle(self.screen, C_FOOD,       (cx, cy), r)
        pygame.draw.circle(self.screen, C_FOOD_SHINE, (cx-3, cy-3), r // 3)
        pygame.draw.line(self.screen, (50, 120, 50), (cx, cy-r), (cx, cy-r-5), 2)
        pygame.draw.polygon(self.screen, C_SNAKE_BODY,
                            [(cx, cy-r-3), (cx+5, cy-r-6), (cx+2, cy-r-2)])

    # ── HUD ───────────────────────────────────
    def _draw_hud(self):
        pad = 8
        self.screen.blit(self.font_xs.render("SCORE", True, C_MUTED), (pad, pad))
        self.screen.blit(self.font_md.render(str(self.score), True, C_GREEN), (pad, pad+14))

        diff_col = {"Easy": C_GREEN, "Medium": C_GOLD, "Hard": C_RED}[self.difficulty]
        d = self.font_xs.render(f"● {self.difficulty.upper()}", True, diff_col)
        self.screen.blit(d, (SCREEN_W//2 - d.get_width()//2, pad+4))

        h_lbl = self.font_xs.render("BEST", True, C_MUTED)
        h_val = self.font_md.render(str(self.highscore), True, C_GOLD)
        self.screen.blit(h_lbl, (SCREEN_W - h_lbl.get_width() - pad, pad))
        self.screen.blit(h_val, (SCREEN_W - h_val.get_width() - pad, pad+14))

        self._draw_watermark()

    # ══════════════════════════════════════════
    #  Watermark / authorship stamp
    # ══════════════════════════════════════════
    def _draw_watermark(self):
        """
        Renders a semi-transparent copyright notice at the bottom of the screen.
        This identifies the original author visually inside the running game.
        Removing or hiding this watermark does not remove the legal copyright
        declared at the top of this file.
        """
        wm = self.font_xs.render(COPYRIGHT, True, (60, 70, 90))
        wm.set_alpha(140)
        x = SCREEN_W // 2 - wm.get_width() // 2
        y = SCREEN_H - wm.get_height() - 4
        self.screen.blit(wm, (x, y))

    # ══════════════════════════════════════════
    #  Overlay / popup helpers
    # ══════════════════════════════════════════
    def _draw_overlay(self, colour=(10, 14, 26), alpha=190):
        self._overlay_surf.fill((*colour, alpha))
        self.screen.blit(self._overlay_surf, (0, 0))

    def _draw_panel(self, rect, border_col, bg=(12, 18, 34)):
        s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        s.fill((*bg, 230))
        self.screen.blit(s, rect.topleft)
        pygame.draw.rect(self.screen, border_col, rect, 2, border_radius=14)

    def _draw_button(self, text, rect, col, hover=False):
        if hover:
            hb = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            hb.fill((*col, 40))
            self.screen.blit(hb, rect.topleft)
        pygame.draw.rect(self.screen, col, rect, 2, border_radius=8)
        lbl = self.font_sm.render(text, True, col)
        self.screen.blit(lbl, lbl.get_rect(center=rect.center))

    # ── SPLASH (copyright screen on launch) ──
    def _draw_splash(self):
        elapsed  = pygame.time.get_ticks() - self._splash_start
        progress = min(1.0, elapsed / self.SPLASH_DURATION)

        # fade-in for first 0.4 s, fade-out for last 0.4 s
        fade_ms  = 400
        if elapsed < fade_ms:
            alpha = int((elapsed / fade_ms) * 255)
        elif elapsed > self.SPLASH_DURATION - fade_ms:
            alpha = int(((self.SPLASH_DURATION - elapsed) / fade_ms) * 255)
        else:
            alpha = 255

        self.screen.fill(C_BG)

        # thin animated border that fills up like a progress bar
        bar_w = int(SCREEN_W * progress)
        pygame.draw.rect(self.screen, C_GREEN, (0, SCREEN_H - 3, bar_w, 3))

        # ── content surface (so we can alpha-blend the whole thing) ──
        surf = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)

        # snake logo small
        logo = self.font_lg.render("SNAKE", True, C_GREEN)
        surf.blit(logo, logo.get_rect(centerx=SCREEN_W//2, top=110))

        edition = self.font_xs.render("2025 EDITION", True, C_MUTED)
        surf.blit(edition, edition.get_rect(centerx=SCREEN_W//2, top=162))

        # divider
        pygame.draw.rect(surf, (30, 45, 65),
                         (SCREEN_W//2 - 160, 195, 320, 1))

        # copyright box
        lines = [
            ("© 2025  Christo Joseph",                  C_WHITE,  self.font_md),
            ("All rights reserved.",                    C_MUTED,  self.font_sm),
            ("",                                        C_MUTED,  self.font_xs),
            ("BTEC Level 3 Extended Diploma in IT",     (100,120,150), self.font_sm),
            ("Unit 4 Programming Assignment 2",         (100,120,150), self.font_sm),
            ("",                                        C_MUTED,  self.font_xs),
            ("Slough and Langley College",              C_MUTED,  self.font_xs),
            ("Student ID:  326493",                     C_MUTED,  self.font_xs),
        ]

        y = 215
        for text, colour, font in lines:
            if text == "":
                y += 8
                continue
            s = font.render(text, True, colour)
            surf.blit(s, s.get_rect(centerx=SCREEN_W//2, top=y))
            y += s.get_height() + 5

        # divider
        pygame.draw.rect(surf, (30, 45, 65),
                         (SCREEN_W//2 - 160, y + 6, 320, 1))
        y += 18

        # licence notice
        notice_lines = [
            "This software is the original work of the author above.",
            "Unauthorised copying, modification or redistribution",
            "is strictly prohibited without written permission.",
        ]
        for nl in notice_lines:
            s = self.font_xs.render(nl, True, (55, 65, 80))
            surf.blit(s, s.get_rect(centerx=SCREEN_W//2, top=y))
            y += s.get_height() + 3

        # skip hint  (pulse on/off)
        if int(elapsed / 500) % 2 == 0:
            skip = self.font_xs.render("Press any key or click to continue", True, (45, 55, 70))
            surf.blit(skip, skip.get_rect(centerx=SCREEN_W//2, top=SCREEN_H - 28))

        surf.set_alpha(alpha)
        self.screen.blit(surf, (0, 0))

    # ── MENU ──────────────────────────────────
    def _draw_menu(self):
        self._draw_overlay(alpha=235)

        title = self.font_xl.render("SNAKE", True, C_GREEN)
        self.screen.blit(title, title.get_rect(centerx=SCREEN_W//2, top=80))
        sub = self.font_xs.render("2025  EDITION", True, C_MUTED)
        self.screen.blit(sub, sub.get_rect(centerx=SCREEN_W//2, top=150))

        if self.highscore > 0:
            hs = self.font_sm.render(f"★  High Score: {self.highscore}  ★", True, C_GOLD)
            self.screen.blit(hs, hs.get_rect(centerx=SCREEN_W//2, top=178))

        labels = ["Easy", "Medium", "Hard"]
        cols   = [C_GREEN, C_GOLD, C_RED]
        bw, bh, gap = 140, 44, 20
        total = len(labels)*bw + (len(labels)-1)*gap
        bx, by = (SCREEN_W - total)//2, 240

        ch = self.font_sm.render("— Choose Difficulty —", True, C_MUTED)
        self.screen.blit(ch, ch.get_rect(centerx=SCREEN_W//2, top=by-30))

        self._menu_rects = {}
        for i, (lbl, col) in enumerate(zip(labels, cols)):
            rect = pygame.Rect(bx + i*(bw+gap), by, bw, bh)
            self._menu_rects[lbl] = rect
            self._draw_button(lbl.upper(), rect, col, hover=(self._menu_hover == lbl))

        for j, h in enumerate(["Arrow Keys  –  Move",
                                "ESC / P     –  Pause",
                                "R  –  Restart     M  –  Menu"]):
            s = self.font_xs.render(h, True, C_MUTED)
            self.screen.blit(s, s.get_rect(centerx=SCREEN_W//2, top=340+j*22))

        self._draw_watermark()

    def _hovered_button(self, pos):
        for lbl, rect in self._menu_rects.items():
            if rect.collidepoint(pos):
                return lbl
        return None

    # ── PAUSE ─────────────────────────────────
    def _draw_popup_paused(self):
        self._draw_overlay(alpha=170)
        pw, ph = 380, 280
        panel  = pygame.Rect((SCREEN_W-pw)//2, (SCREEN_H-ph)//2, pw, ph)
        self._draw_panel(panel, C_PAUSE)

        t = self.font_lg.render("PAUSED", True, C_CYAN)
        self.screen.blit(t, t.get_rect(centerx=SCREEN_W//2, top=panel.top+40))

        for i, ln in enumerate(["ESC / C  –  Continue",
                                 "R        –  Restart",
                                 "M        –  Menu"]):
            s = self.font_sm.render(ln, True, C_MUTED)
            self.screen.blit(s, s.get_rect(centerx=SCREEN_W//2, top=panel.top+130+i*32))

    # ── GAME OVER ─────────────────────────────
    def _draw_popup_gameover(self):
        self._draw_overlay((20, 0, 0), 200)
        pw, ph = 420, 340
        panel  = pygame.Rect((SCREEN_W-pw)//2, (SCREEN_H-ph)//2, pw, ph)
        self._draw_panel(panel, C_RED, bg=(28, 6, 6))

        icon = self.font_lg.render("GAME OVER", True, C_RED)
        self.screen.blit(icon, icon.get_rect(centerx=SCREEN_W//2, top=panel.top+20))
        pygame.draw.rect(self.screen, (80,20,20),
                         (panel.left+20, panel.top+70, panel.w-40, 1))

        sl = self.font_sm.render("YOUR SCORE", True, C_MUTED)
        sv = self.font_lg.render(str(self.score), True, C_WHITE)
        self.screen.blit(sl, sl.get_rect(centerx=SCREEN_W//2, top=panel.top+82))
        self.screen.blit(sv, sv.get_rect(centerx=SCREEN_W//2, top=panel.top+104))

        if self.score > 0 and self.score >= self.highscore:
            ht = self.font_sm.render("NEW HIGH SCORE!", True, C_GOLD)
        else:
            ht = self.font_xs.render(f"Best: {self.highscore}", True, C_GOLD)
        self.screen.blit(ht, ht.get_rect(centerx=SCREEN_W//2, top=panel.top+158))

        et = self.font_xs.render(f"Apples eaten: {self.food_eaten}", True, C_MUTED)
        self.screen.blit(et, et.get_rect(centerx=SCREEN_W//2, top=panel.top+188))
        pygame.draw.rect(self.screen, (80,20,20),
                         (panel.left+20, panel.top+216, panel.w-40, 1))

        bw, bh, gap = 150, 38, 20
        bx = (SCREEN_W - (2*bw+gap)) // 2
        for i, (txt, col) in enumerate([("[ R ]  Retry", C_GREEN),
                                         ("[ M ]  Menu",  C_MUTED)]):
            self._draw_button(txt, pygame.Rect(bx+i*(bw+gap), panel.top+234, bw, bh), col)

    # ── WIN ───────────────────────────────────
    def _draw_popup_win(self):
        self._draw_overlay((0, 20, 0), 200)
        pw, ph = 440, 360
        panel  = pygame.Rect((SCREEN_W-pw)//2, (SCREEN_H-ph)//2, pw, ph)
        self._draw_panel(panel, C_GREEN, bg=(5, 25, 8))

        pulse = abs(math.sin(pygame.time.get_ticks() * 0.003))
        gc    = lerp_colour((57, 200, 20), C_GREEN, pulse)
        title = self.font_lg.render("YOU WIN!", True, gc)
        self.screen.blit(title, title.get_rect(centerx=SCREEN_W//2, top=panel.top+22))
        pygame.draw.rect(self.screen, (20,80,20),
                         (panel.left+20, panel.top+74, panel.w-40, 1))

        fl = self.font_sm.render("FINAL SCORE", True, C_MUTED)
        fv = self.font_lg.render(str(self.score), True, C_GREEN)
        self.screen.blit(fl, fl.get_rect(centerx=SCREEN_W//2, top=panel.top+90))
        self.screen.blit(fv, fv.get_rect(centerx=SCREEN_W//2, top=panel.top+114))

        hs_txt = "NEW HIGH SCORE!" if self.score >= self.highscore else f"High Score: {self.highscore}"
        hs = self.font_sm.render(hs_txt, True, C_GOLD)
        self.screen.blit(hs, hs.get_rect(centerx=SCREEN_W//2, top=panel.top+170))

        msg = self.font_xs.render("You filled the board — incredible!", True, C_MUTED)
        self.screen.blit(msg, msg.get_rect(centerx=SCREEN_W//2, top=panel.top+210))
        pygame.draw.rect(self.screen, (20,80,20),
                         (panel.left+20, panel.top+238, panel.w-40, 1))

        bw, bh, gap = 160, 38, 20
        bx = (SCREEN_W - (2*bw+gap)) // 2
        for i, (txt, col) in enumerate([("[ R ]  Play Again", C_GREEN),
                                         ("[ M ]  Menu",       C_MUTED)]):
            self._draw_button(txt, pygame.Rect(bx+i*(bw+gap), panel.top+258, bw, bh), col)

    # ─────────────────────────────────────────
    def _quit(self):
        pygame.quit()
        sys.exit()