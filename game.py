# ─────────────────────────────────────────────
#  game.py  –  Game loop, states, rendering, UI
# ─────────────────────────────────────────────
import pygame, sys, math, random
from settings import *
from snake  import Snake
from food   import Food
from utils  import load_highscore, save_highscore
from typing import Tuple


# ══════════════════════════════════════════════
#  Particle  (eat / win / death effects)
# ══════════════════════════════════════════════
class Particle:: float, y: float, colour: Tuple[int, int, int]
    def __init__(self, x, y, colour):
        angle  = random.uniform(0, math.pi * 2)
        speed  = random.uniform(1.5, 5)
        self.x = x;  self.y = y
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = 1.0
        self.colour = colour
        self.radius = random.randint(2, 5)

    def update(self):
        self.x  += self.vx
        self.y  += self.vy
        self.vy += 0.15          # gravity
        self.life -= 0.035

    def draw(self, surface):
        if self.life <= 0:
            return
        alpha = int(self.life * 255)
        col   = (*self.colour, alpha)
        s = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, col, (self.radius, self.radius), self.radius)
        surface.blit(s, (int(self.x - self.radius), int(self.y - self.radius)))


# ══════════════════════════════════════════════
#  FloatText  ("+20" pop-up over food)
# ══════════════════════════════════════════════
class FloatText:
    def __init__(self, text, x, y, colour, font):
        self.text   = text
        self.x, self.y = x, y
        self.colour = colour
        self.font   = font
        self.life   = 1.0
        self.vy     = -1.8

    def update(self):
        self.y    += self.vy
        self.life -= 0.03

    def draw(self, surface):
        if self.life <= 0:
            return
        alpha = int(self.life * 255)
        surf  = self.font.render(self.text, True, self.colour)
        surf.set_alpha(alpha)
        surface.blit(surf, (self.x - surf.get_width() // 2, int(self.y)))


# ══════════════════════════════════════════════
#  Game
# ══════════════════════════════════════════════
class Game:
    # ── states ───────────────────────────────
    MENU     = "menu"
    PLAYING  = "playing"
    PAUSED   = "paused"
    GAMEOVER = "gameover"
    WIN      = "win"

    def __init__(self):
        pygame.init()
        pygame.display.set_caption(TITLE)
        self.screen  = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self.clock   = pygame.time.Clock()

        # fonts
        self.font_xl  = pygame.font.SysFont("consolas", 62, bold=True)
        self.font_lg  = pygame.font.SysFont("consolas", 38, bold=True)
        self.font_md  = pygame.font.SysFont("consolas", 22, bold=True)
        self.font_sm  = pygame.font.SysFont("consolas", 16)
        self.font_xs  = pygame.font.SysFont("consolas", 13)

        self.highscore = load_highscore()
        self.state     = self.MENU
        self.difficulty = "Medium"

        # game objects (initialised in new_game)
        self.snake     = None
        self.food      = None
        self.score     = 0
        self.food_eaten = 0

        # animation / effect state
        self.particles : list[Particle]  = []
        self.floats    : list[FloatText] = []
        self.flash_alpha = 0        # green flash on eat
        self.death_shake = 0        # screen shake frames
        self.shake_offset = (0, 0)
        self.grid_pulse  = 0.0      # subtle grid glow
        self.win_burst_done = False

        # tick timer
        self._tick_event = pygame.USEREVENT + 1
        self._set_speed()

        # menu selection highlight
        self._menu_hover = None

    # ── difficulty helpers ───────────────────
    def _set_speed(self):
        delay, _ = DIFFICULTIES[self.difficulty]
        pygame.time.set_timer(self._tick_event, delay)

    def _points_per_food(self):
        return DIFFICULTIES[self.difficulty][1]

    # ── game lifecycle ───────────────────────
    def new_game(self):
        self.snake      = Snake()
        self.food       = Food(self.snake.body)
        self.score      = 0
        self.food_eaten = 0
        self.particles.clear()
        self.floats.clear()
        self.flash_alpha  = 0
        self.death_shake  = 0
        self.win_burst_done = False
        self._set_speed()
        self.state = self.PLAYING

    # ── main loop ────────────────────────────
    def run(self):
        while True:
            self._handle_events()
            self._update()
            self._draw()
            self.clock.tick(FPS)

    # ── events ───────────────────────────────
    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._quit()

            # ── keyboard ─────────────────────
            if event.type == pygame.KEYDOWN:
                self._on_key(event.key)

            # ── game tick ────────────────────
            if event.type == self._tick_event and self.state == self.PLAYING:
                self._game_tick()

            # ── mouse (menu buttons) ──────────
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._on_click(event.pos)

        # track hover for menu buttons
        if self.state == self.MENU:
            self._menu_hover = self._hovered_button(pygame.mouse.get_pos())

    def _on_key(self, key):
        s = self.state
        # arrow keys always available while playing
        if s == self.PLAYING:
            if   key == pygame.K_UP:    self.snake.change_direction((0, -1))
            elif key == pygame.K_DOWN:  self.snake.change_direction((0,  1))
            elif key == pygame.K_LEFT:  self.snake.change_direction((-1, 0))
            elif key == pygame.K_RIGHT: self.snake.change_direction(( 1, 0))
            elif key == pygame.K_ESCAPE or key == pygame.K_p:
                self.state = self.PAUSED
        elif s == self.PAUSED:
            if key in (pygame.K_ESCAPE, pygame.K_c, pygame.K_p):
                self.state = self.PLAYING
            elif key == pygame.K_r:
                self.new_game()
            elif key == pygame.K_m:
                self.state = self.MENU
        elif s == self.GAMEOVER:
            if key == pygame.K_r:
                self.new_game()
            elif key == pygame.K_m:
                self.state = self.MENU
        elif s == self.WIN:
            if key == pygame.K_r:
                self.new_game()
            elif key == pygame.K_m:
                self.state = self.MENU

    def _on_click(self, pos):
        if self.state == self.MENU:
            btn = self._hovered_button(pos)
            if btn in DIFFICULTIES:
                self.difficulty = btn
                self.new_game()

    # ── game logic tick ──────────────────────
    def _game_tick(self):
        self.snake.move()

        if self.snake.hit_wall() or self.snake.hit_self():
            self._trigger_death()
            return

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

        # visual effects
        fx, fy = self._cell_centre(self.food.position)
        colours = [C_GREEN, C_GOLD, C_CYAN, C_FOOD]
        for _ in range(14):
            self.particles.append(Particle(fx, fy, random.choice(colours)))
        self.floats.append(FloatText(f"+{pts}", fx, fy - 10, C_GOLD, self.font_md))
        self.flash_alpha = 55

        self.snake.grow()
        self.food.respawn(self.snake.body)

    def _trigger_death(self):
        pygame.time.set_timer(self._tick_event, 0)
        self.state = self.GAMEOVER
        self.death_shake = 22
        hx, hy = self._cell_centre(self.snake.head)
        for _ in range(35):
            self.particles.append(Particle(hx, hy, random.choice([C_RED, (255,140,0)])))

    def _trigger_win(self):
        pygame.time.set_timer(self._tick_event, 0)
        self.state = self.WIN

    # ── update (per-frame, 60 fps) ───────────
    def _update(self):
        self.grid_pulse = (self.grid_pulse + 0.04) % (math.pi * 2)

        for p in self.particles:  p.update()
        self.particles = [p for p in self.particles if p.life > 0]

        for f in self.floats:     f.update()
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

        # win burst particles
        if self.state == self.WIN and not self.win_burst_done:
            self.win_burst_done = True
            for _ in range(60):
                x = random.randint(GRID_OFFSET_X, GRID_OFFSET_X + GRID_W)
                y = random.randint(GRID_OFFSET_Y, GRID_OFFSET_Y + GRID_H)
                col = random.choice([C_GREEN, C_GOLD, C_CYAN, (255,100,200)])
                self.particles.append(Particle(x, y, col))

    # ══════════════════════════════════════════
    #  DRAWING
    # ══════════════════════════════════════════
    def _draw(self):
        ox, oy = self.shake_offset

        # background
        self.screen.fill(C_BG)

        # grid
        self._draw_grid(ox, oy)

        # game objects
        if self.state != self.MENU:
            self._draw_food(ox, oy)
            alpha = 100 if self.state in (self.GAMEOVER, self.WIN) else 255
            self._draw_snake(ox, oy, alpha)

        # particles & floats (always on top of grid)
        for p in self.particles: p.draw(self.screen)
        for f in self.floats:    f.draw(self.screen)

        # green flash overlay
        if self.flash_alpha > 0:
            flash = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            flash.fill((57, 255, 20, self.flash_alpha))
            self.screen.blit(flash, (0, 0))

        # HUD
        if self.state in (self.PLAYING, self.PAUSED, self.GAMEOVER, self.WIN):
            self._draw_hud()

        # overlays
        if self.state == self.MENU:
            self._draw_menu()
        elif self.state == self.PAUSED:
            self._draw_popup_paused()
        elif self.state == self.GAMEOVER:
            self._draw_popup_gameover()
        elif self.state == self.WIN:
            self._draw_popup_win()

        pygame.display.flip()

    # ── grid ─────────────────────────────────
    def _draw_grid(self, ox=0, oy=0):
        alpha = int(8 + math.sin(self.grid_pulse) * 4)
        col   = (30 + alpha, 50 + alpha, 80 + alpha)
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
        # border
        pygame.draw.rect(self.screen, (40, 60, 90),
                         (GRID_OFFSET_X + ox - 1, GRID_OFFSET_Y + oy - 1,
                          GRID_W + 2, GRID_H + 2), 2)

    # ── snake ────────────────────────────────
    def _draw_snake(self, ox=0, oy=0, alpha=255):
        n = len(self.snake)
        for i, seg in enumerate(self.snake.body):
            t   = 1 - i / n
            col = self._lerp_colour(C_SNAKE_TAIL, C_SNAKE_HEAD, t)
            if i == 0:
                col = C_SNAKE_HEAD
            pad = 3 if i > 0 else 2
            x = GRID_OFFSET_X + seg[0] * CELL + pad + ox
            y = GRID_OFFSET_Y + seg[1] * CELL + pad + oy
            sz = CELL - pad * 2
            r  = 5 if i == 0 else 3
            rect = pygame.Rect(x, y, sz, sz)

            # draw with alpha via surface
            s = pygame.Surface((sz, sz), pygame.SRCALPHA)
            pygame.draw.rect(s, (*col, alpha), (0, 0, sz, sz), border_radius=r)

            # glow on head
            if i == 0:
                glow = pygame.Surface((sz + 8, sz + 8), pygame.SRCALPHA)
                pygame.draw.rect(glow, (*C_SNAKE_HEAD, 40),
                                 (0, 0, sz + 8, sz + 8), border_radius=r + 3)
                self.screen.blit(glow, (x - 4, y - 4))

            self.screen.blit(s, (x, y))

            # eyes on head
            if i == 0:
                self._draw_eyes(seg, ox, oy)

    def _draw_eyes(self, seg, ox, oy):
        dx, dy = self.snake.direction
        cx = GRID_OFFSET_X + seg[0] * CELL + CELL // 2 + ox
        cy = GRID_OFFSET_Y + seg[1] * CELL + CELL // 2 + oy

        # perpendicular offset for two eyes
        eye_offsets = {
            (1,0):  [( 3,-4),( 3, 4)],
            (-1,0): [(-3,-4),(-3, 4)],
            (0,-1): [(-4,-3),( 4,-3)],
            (0, 1): [(-4, 3),( 4, 3)],
        }
        for ex, ey in eye_offsets.get((dx, dy), [(3,-4),(3,4)]):
            pygame.draw.circle(self.screen, (5, 10, 20),   (cx+ex, cy+ey), 3)
            pygame.draw.circle(self.screen, C_SNAKE_HEAD,  (cx+ex-1, cy+ey-1), 1)

    # ── food ─────────────────────────────────
    def _draw_food(self, ox=0, oy=0):
        fx, fy = self.food.position
        bob    = self.food.bob_offset()
        cx = GRID_OFFSET_X + fx * CELL + CELL // 2 + ox
        cy = int(GRID_OFFSET_Y + fy * CELL + CELL // 2 + bob) + oy
        r  = CELL // 2 - 3

        # glow aura
        aura = pygame.Surface((r*4, r*4), pygame.SRCALPHA)
        pygame.draw.circle(aura, (*C_FOOD, 40), (r*2, r*2), r*2)
        self.screen.blit(aura, (cx - r*2, cy - r*2))

        # apple body
        pygame.draw.circle(self.screen, C_FOOD,       (cx, cy), r)
        pygame.draw.circle(self.screen, C_FOOD_SHINE, (cx-3, cy-3), r//3)

        # stem
        pygame.draw.line(self.screen, (50, 120, 50), (cx, cy - r), (cx, cy - r - 5), 2)
        # leaf
        leaf_pts = [(cx, cy-r-3), (cx+5, cy-r-6), (cx+2, cy-r-2)]
        pygame.draw.polygon(self.screen, C_SNAKE_BODY, leaf_pts)

    # ── HUD ──────────────────────────────────
    def _draw_hud(self):
        pad = 8
        # score
        s_lbl = self.font_xs.render("SCORE", True, C_MUTED)
        s_val = self.font_md.render(str(self.score), True, C_GREEN)
        self.screen.blit(s_lbl, (pad, pad))
        self.screen.blit(s_val, (pad, pad + 14))
        # difficulty badge
        diff_col = {"Easy": C_GREEN, "Medium": C_GOLD, "Hard": C_RED}[self.difficulty]
        d_surf = self.font_xs.render(f"● {self.difficulty.upper()}", True, diff_col)
        self.screen.blit(d_surf, (SCREEN_W // 2 - d_surf.get_width() // 2, pad + 4))
        # high score
        h_lbl = self.font_xs.render("BEST", True, C_MUTED)
        h_val = self.font_md.render(str(self.highscore), True, C_GOLD)
        self.screen.blit(h_lbl, (SCREEN_W - h_lbl.get_width() - pad, pad))
        self.screen.blit(h_val, (SCREEN_W - h_val.get_width() - pad, pad + 14))

    # ══════════════════════════════════════════
    #  POPUP / OVERLAY helpers
    # ══════════════════════════════════════════
    def _draw_overlay(self, colour=(10, 14, 26), alpha=190):
        ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        ov.fill((*colour, alpha))
        self.screen.blit(ov, (0, 0))

    def _draw_panel(self, rect, border_col, bg=(12, 18, 34)):
        panel = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        panel.fill((*bg, 230))
        self.screen.blit(panel, rect.topleft)
        pygame.draw.rect(self.screen, border_col, rect, 2, border_radius=14)

    def _draw_button(self, text, rect, col, hover=False):
        bg = (*col, 40) if hover else (0, 0, 0, 0)
        btn = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        btn.fill(bg)
        self.screen.blit(btn, rect.topleft)
        pygame.draw.rect(self.screen, col, rect, 2, border_radius=8)
        lbl = self.font_sm.render(text, True, col)
        self.screen.blit(lbl, lbl.get_rect(center=rect.center))

    # ── MENU ─────────────────────────────────
    def _draw_menu(self):
        self._draw_overlay(alpha=235)

        # title
        title = self.font_xl.render("SNAKE", True, C_GREEN)
        glow  = pygame.transform.scale(title, (title.get_width()+10, title.get_height()+10))
        self.screen.blit(title, title.get_rect(centerx=SCREEN_W//2, top=80))

        sub = self.font_xs.render("2025  EDITION", True, C_MUTED)
        self.screen.blit(sub, sub.get_rect(centerx=SCREEN_W//2, top=148))

        # high score banner
        if self.highscore > 0:
            hs = self.font_sm.render(f"★  High Score: {self.highscore}  ★", True, C_GOLD)
            self.screen.blit(hs, hs.get_rect(centerx=SCREEN_W//2, top=178))

        # difficulty buttons
        labels = ["Easy", "Medium", "Hard"]
        cols   = [C_GREEN, C_GOLD, C_RED]
        bw, bh, gap = 140, 44, 20
        total  = len(labels) * bw + (len(labels)-1) * gap
        bx     = (SCREEN_W - total) // 2
        by     = 240

        choose = self.font_sm.render("— Choose Difficulty —", True, C_MUTED)
        self.screen.blit(choose, choose.get_rect(centerx=SCREEN_W//2, top=by - 30))

        self._menu_rects = {}
        for i, (lbl, col) in enumerate(zip(labels, cols)):
            rect = pygame.Rect(bx + i*(bw+gap), by, bw, bh)
            self._menu_rects[lbl] = rect
            hover = (self._menu_hover == lbl)
            self._draw_button(lbl.upper(), rect, col, hover)

        # controls hint
        hints = [
            "Arrow Keys  –  Move",
            "ESC / P     –  Pause",
            "R           –  Restart   M  –  Menu",
        ]
        for j, h in enumerate(hints):
            s = self.font_xs.render(h, True, C_MUTED)
            self.screen.blit(s, s.get_rect(centerx=SCREEN_W//2, top=340 + j*22))

    def _hovered_button(self, pos):
        if not hasattr(self, "_menu_rects"):
            return None
        for lbl, rect in self._menu_rects.items():
            if rect.collidepoint(pos):
                return lbl
        return None

    # ── PAUSE popup ──────────────────────────
    def _draw_popup_paused(self):
        self._draw_overlay(alpha=170)
        pw, ph = 380, 280
        panel  = pygame.Rect((SCREEN_W-pw)//2, (SCREEN_H-ph)//2, pw, ph)
        self._draw_panel(panel, C_PAUSE)

        icon = self.font_lg.render("⏸", True, C_CYAN)
        self.screen.blit(icon, icon.get_rect(centerx=SCREEN_W//2, top=panel.top+24))

        title = self.font_lg.render("PAUSED", True, C_CYAN)
        self.screen.blit(title, title.get_rect(centerx=SCREEN_W//2, top=panel.top+70))

        lines = ["ESC / C  –  Continue", "R        –  Restart", "M        –  Menu"]
        for i, ln in enumerate(lines):
            s = self.font_sm.render(ln, True, C_MUTED)
            self.screen.blit(s, s.get_rect(centerx=SCREEN_W//2, top=panel.top+140+i*30))

    # ── GAME OVER popup ──────────────────────
    def _draw_popup_gameover(self):
        self._draw_overlay((20, 0, 0), 200)
        pw, ph = 420, 340
        panel  = pygame.Rect((SCREEN_W-pw)//2, (SCREEN_H-ph)//2, pw, ph)
        self._draw_panel(panel, C_RED, bg=(28, 6, 6))

        icon = self.font_lg.render("💀  GAME OVER  💀", True, C_RED)
        self.screen.blit(icon, icon.get_rect(centerx=SCREEN_W//2, top=panel.top+20))

        sep = pygame.Rect(panel.left+20, panel.top+75, panel.w-40, 1)
        pygame.draw.rect(self.screen, (80, 20, 20), sep)

        score_lbl = self.font_sm.render("YOUR SCORE", True, C_MUTED)
        score_val = self.font_lg.render(str(self.score), True, C_WHITE)
        self.screen.blit(score_lbl, score_lbl.get_rect(centerx=SCREEN_W//2, top=panel.top+90))
        self.screen.blit(score_val, score_val.get_rect(centerx=SCREEN_W//2, top=panel.top+112))

        if self.score >= self.highscore and self.score > 0:
            new_hs = self.font_sm.render("🏆  NEW HIGH SCORE!", True, C_GOLD)
            self.screen.blit(new_hs, new_hs.get_rect(centerx=SCREEN_W//2, top=panel.top+162))
        else:
            best = self.font_xs.render(f"Best: {self.highscore}", True, C_GOLD)
            self.screen.blit(best, best.get_rect(centerx=SCREEN_W//2, top=panel.top+162))

        eaten = self.font_xs.render(f"Apples eaten: {self.food_eaten}", True, C_MUTED)
        self.screen.blit(eaten, eaten.get_rect(centerx=SCREEN_W//2, top=panel.top+192))

        sep2 = pygame.Rect(panel.left+20, panel.top+222, panel.w-40, 1)
        pygame.draw.rect(self.screen, (80, 20, 20), sep2)

        btns = [("[ R ]  Retry", C_GREEN), ("[ M ]  Menu", C_MUTED)]
        bw, bh = 150, 38
        gap = 20
        total = len(btns)*bw + (len(btns)-1)*gap
        bx = (SCREEN_W - total) // 2
        for i, (txt, col) in enumerate(btns):
            rect = pygame.Rect(bx + i*(bw+gap), panel.top+242, bw, bh)
            self._draw_button(txt, rect, col)

    # ── WIN popup ────────────────────────────
    def _draw_popup_win(self):
        self._draw_overlay((0, 20, 0), 200)
        pw, ph = 440, 360
        panel  = pygame.Rect((SCREEN_W-pw)//2, (SCREEN_H-ph)//2, pw, ph)
        self._draw_panel(panel, C_GREEN, bg=(5, 25, 8))

        # animated glow title
        pulse = abs(math.sin(pygame.time.get_ticks() * 0.003))
        gl = int(150 + pulse * 105)
        glow_col = (50, gl, 50)
        title = self.font_lg.render("🏆  YOU WIN!  🏆", True, C_GREEN)
        self.screen.blit(title, title.get_rect(centerx=SCREEN_W//2, top=panel.top+20))

        sep = pygame.Rect(panel.left+20, panel.top+75, panel.w-40, 1)
        pygame.draw.rect(self.screen, (20, 80, 20), sep)

        lbl = self.font_sm.render("FINAL SCORE", True, C_MUTED)
        val = self.font_lg.render(str(self.score), True, C_GREEN)
        self.screen.blit(lbl, lbl.get_rect(centerx=SCREEN_W//2, top=panel.top+92))
        self.screen.blit(val, val.get_rect(centerx=SCREEN_W//2, top=panel.top+116))

        hs_txt = "★  NEW HIGH SCORE  ★" if self.score >= self.highscore else f"High Score: {self.highscore}"
        hs = self.font_sm.render(hs_txt, True, C_GOLD)
        self.screen.blit(hs, hs.get_rect(centerx=SCREEN_W//2, top=panel.top+172))

        msg = self.font_xs.render("Incredible! You filled the entire board!", True, C_MUTED)
        self.screen.blit(msg, msg.get_rect(centerx=SCREEN_W//2, top=panel.top+212))

        sep2 = pygame.Rect(panel.left+20, panel.top+240, panel.w-40, 1)
        pygame.draw.rect(self.screen, (20, 80, 20), sep2)

        btns = [("[ R ]  Play Again", C_GREEN), ("[ M ]  Menu", C_MUTED)]
        bw, bh = 160, 38
        gap = 20
        total = len(btns)*bw + (len(btns)-1)*gap
        bx = (SCREEN_W - total) // 2
        for i, (txt, col) in enumerate(btns):
            rect = pygame.Rect(bx + i*(bw+gap), panel.top+260, bw, bh)
            self._draw_button(txt, rect, col)

    # ── helpers ──────────────────────────────
    def _cell_centre(self, pos) -> tuple[int, int]:
        return (GRID_OFFSET_X + pos[0] * CELL + CELL // 2,
                GRID_OFFSET_Y + pos[1] * CELL + CELL // 2)

    @staticmethod
    def _lerp_colour(a, b, t):
        return tuple(int(a[i] + (b[i]-a[i])*t) for i in range(3))

    def _quit(self):
        pygame.quit()
        sys.exit()