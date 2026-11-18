"""A Constellation for Valbb ♡

Controles:  ESPACIO = pausa/continuar  |  ESC = salir
"""

import math
import random
import time
import tkinter
import turtle
from functools import lru_cache

# ----------------------------------------------------------------------
# Configuración
# ----------------------------------------------------------------------
WIDTH, HEIGHT = 1000, 700
FPS = 30
FRAME_MS = 1000 // FPS
BG = "#080D24"

# Línea de tiempo del ciclo (segundos)
CYCLE = 15.0
T_HEART = 6.0            # el corazón se dibuja de 0 a 6 s
T_INNER_START = 6.0      # la "V" interior aparece de 6 a 8.2 s
T_INNER_END = 8.2
T_TEXT = 8.2             # el mensaje aparece a los 8.2 s
T_TEXT_FADE = 1.4
T_SHOOT = (9.5, 10.5)    # estrella fugaz
T_FADE_OUT = 13.5        # desvanecimiento final antes de repetir

HEART_STARS = [
    (-210, 105), (-180, 155), (-125, 180), (-65, 155),
    (0, 105), (65, 155), (125, 180), (180, 155),
    (210, 105), (215, 45), (185, -15), (135, -70),
    (75, -125), (0, -190), (-75, -125), (-135, -70),
    (-185, -15), (-215, 45),
]

INNER_STARS = [
    (-100, 85), (-78, 35), (-52, -15), (-25, -65), (0, -105),
    (25, -65), (52, -15), (78, 35), (100, 85),
]

STAR_COLORS = ["#FFF4D2", "#DCE9FF", "#F8D9EA", "#D7D9FF"]
LINE_COLOR = "#91A8D8"
INNER_COLOR = "#E8D8FF"
GOLD = "#FFF4D2"

DISTANT = [
    (-445, 275, 1.7), (-390, 160, 1.3), (-350, 300, 1.5), (-300, -40, 1.2),
    (-260, 260, 1.1), (-175, 285, 1.5), (-95, 245, 1.1), (85, 280, 1.4),
    (165, 250, 1.1), (280, 290, 1.7), (390, 230, 1.2), (445, 90, 1.5),
    (410, -120, 1.2), (320, -260, 1.6), (220, -300, 1.1), (70, -275, 1.3),
    (-110, -290, 1.5), (-330, -230, 1.2), (-440, -120, 1.4), (0, 260, 1.0),
    (350, 20, 1.0), (-390, 35, 1.0), (260, 120, 1.2), (-250, -180, 1.0),
]

_rng = random.Random(24)
# (fase, velocidad) de parpadeo para cada estrella lejana
TWINKLE = [(_rng.uniform(0, math.tau), _rng.uniform(0.8, 2.2)) for _ in DISTANT]


# ----------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------
def clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


def smooth(v):
    """Interpolación suave (ease in-out) en [0, 1]."""
    v = clamp(v)
    return v * v * (3 - 2 * v)


@lru_cache(maxsize=None)
def _rgb(color):
    return (int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16))


@lru_cache(maxsize=8192)
def _tint(color, alpha_q):
    """Mezcla `color` con el fondo; alpha_q es alpha cuantizado (0-100)."""
    a = alpha_q / 100
    r1, g1, b1 = _rgb(BG)
    r2, g2, b2 = _rgb(color)
    return "#{:02x}{:02x}{:02x}".format(
        int(r1 + (r2 - r1) * a),
        int(g1 + (g2 - g1) * a),
        int(b1 + (b2 - b1) * a),
    )


def tint(color, alpha=1.0):
    """Simula transparencia mezclando el color con el fondo."""
    return _tint(color, int(clamp(alpha) * 100))


# ----------------------------------------------------------------------
# Primitivas de dibujo
# ----------------------------------------------------------------------
def disc(t, x, y, r, color, steps=14):
    t.penup()
    t.goto(x, y - r)
    t.color(color)
    t.begin_fill()
    t.pendown()
    t.circle(r, steps=steps)
    t.end_fill()
    t.penup()


def line(t, a, b, color, width):
    t.penup()
    t.goto(*a)
    t.pencolor(color)
    t.pensize(width)
    t.pendown()
    t.goto(*b)
    t.penup()


def star(t, x, y, r, color=GOLD, alpha=1.0, glow=True, sparkle=True):
    if alpha <= 0.01:
        return

    if glow:
        for scale, k in ((3.6, 0.09), (2.5, 0.17), (1.7, 0.30)):
            disc(t, x, y, r * scale, tint(color, alpha * k), steps=16)

    disc(t, x, y, r, tint(color, alpha))

    if sparkle:
        c = tint(color, alpha * 0.85)
        long_ = r * 3.0
        short = r * 1.5
        line(t, (x - long_, y), (x + long_, y), c, 1)
        line(t, (x, y - long_), (x, y + long_), c, 1)
        c2 = tint(color, alpha * 0.45)
        line(t, (x - short, y - short), (x + short, y + short), c2, 1)
        line(t, (x - short, y + short), (x + short, y - short), c2, 1)


# ----------------------------------------------------------------------
# Pantalla
# ----------------------------------------------------------------------
screen = turtle.Screen()
screen.setup(WIDTH, HEIGHT)
screen.title("A Constellation for Valbb ♡")
screen.bgcolor(BG)
screen.tracer(0, 0)

pen = turtle.Turtle(visible=False)    # capa estática (se dibuja una vez)
pen.speed(0)
anim = turtle.Turtle(visible=False)   # capa animada (se redibuja cada frame)
anim.speed(0)

paused = False
running = True
clock = 0.0
last_tick = time.perf_counter()


def draw_static():
    """Luna creciente con halo y encabezado."""
    for scale, k in ((1.9, 0.07), (1.5, 0.12), (1.2, 0.22)):
        disc(pen, 365, 261, 31 * scale, tint("#F6E9C5", k), steps=40)
    disc(pen, 365, 261, 31, "#F6E9C5", steps=48)
    disc(pen, 378, 270, 28, BG, steps=48)

    pen.penup()
    pen.goto(0, 285)
    pen.color("#C9D6F2")
    pen.write("Un pedacito del universo para ti",
              align="center", font=("Georgia", 16, "italic"))


# ----------------------------------------------------------------------
# Capas animadas
# ----------------------------------------------------------------------
def draw_twinkle(t):
    for (x, y, r), (phase, speed) in zip(DISTANT, TWINKLE):
        s = 0.5 + 0.5 * math.sin(t * speed + phase)
        disc(anim, x, y, r * (0.8 + 0.5 * s), tint("#AABBE0", 0.35 + 0.65 * s),
             steps=8)
        if s > 0.9:  # destello ocasional
            c = tint("#AABBE0", (s - 0.9) * 8)
            line(anim, (x - r * 3, y), (x + r * 3, y), c, 1)
            line(anim, (x, y - r * 3), (x, y + r * 3), c, 1)


def draw_heart(t, a):
    n = len(HEART_STARS)
    p = n * smooth(t / T_HEART)   # progreso continuo: 0...n

    # Líneas: cada segmento crece suavemente hasta la siguiente estrella.
    for i in range(n):
        frac = clamp(p - i)
        if frac <= 0:
            break
        x1, y1 = HEART_STARS[i]
        x2, y2 = HEART_STARS[(i + 1) % n]
        end = (x1 + (x2 - x1) * frac, y1 + (y2 - y1) * frac)
        line(anim, (x1, y1), end, tint(LINE_COLOR, 0.22 * a), 5)
        line(anim, (x1, y1), end, tint(LINE_COLOR, 0.85 * a), 1.5)

    # Estrellas: aparecen con fundido al ser alcanzadas.
    for i, (x, y) in enumerate(HEART_STARS):
        appear = clamp((p - i) * 3)
        if appear <= 0:
            continue
        pulse = 3.0 + 0.8 * math.sin(t * 2.7 + i * 0.7)
        star(anim, x, y, pulse * (0.5 + 0.5 * appear),
             STAR_COLORS[i % len(STAR_COLORS)], appear * a)


def draw_inner(t, a):
    n = len(INNER_STARS)
    span = (T_INNER_END - T_INNER_START) / n
    for i, (x, y) in enumerate(INNER_STARS):
        appear = clamp((t - T_INNER_START - i * span) * 2.5)
        if appear <= 0:
            continue
        pulse = 2.8 + 1.2 * math.sin(t * 3.6 + i * 0.8)
        star(anim, x, y, pulse * (0.5 + 0.5 * appear), INNER_COLOR, appear * a)

    # Destello especial al completarse la V.
    done = clamp((t - T_INNER_END) * 2)
    if done > 0:
        r = 5 + 2 * math.sin(t * 4.5)
        star(anim, 0, -105, r, GOLD, done * a)


def draw_message(t, a):
    alpha = smooth((t - T_TEXT) / T_TEXT_FADE) * a
    if alpha <= 0.02:
        return

    pulse = 2 + 1.2 * math.sin(t * 2.1)
    for i in range(3):
        disc(anim, 0, -250, (pulse + i * 2) * 3,
             tint("#263A66", alpha * 0.5), steps=16)

    anim.penup()
    anim.goto(0, -265)
    anim.color(tint("#F8E8C8", alpha))
    anim.write("Princesa mía", align="center", font=("Georgia", 28, "bold"))

    anim.goto(0, -310)
    anim.color(tint("#D7DDF2", alpha))
    anim.write("Hasta el cielo encuentra formas de recordarme a ti.",
               align="center", font=("Georgia", 13, "italic"))


def draw_shooting_star(t, a):
    s = (t - T_SHOOT[0]) / (T_SHOOT[1] - T_SHOOT[0])
    if not 0 < s < 1:
        return
    fade = math.sin(math.pi * s) * a
    x0, y0, x1, y1 = -420, 250, -120, 120
    hx, hy = x0 + (x1 - x0) * s, y0 + (y1 - y0) * s
    segments = 8
    for k in range(segments):
        f1 = k / segments
        f2 = (k + 1) / segments
        a1 = (hx - (x1 - x0) * 0.25 * f1, hy - (y1 - y0) * 0.25 * f1)
        a2 = (hx - (x1 - x0) * 0.25 * f2, hy - (y1 - y0) * 0.25 * f2)
        line(anim, a1, a2, tint("#FFF4D2", fade * (1 - f1)), 3 - 2 * f1)
    disc(anim, hx, hy, 2.5, tint("#FFFFFF", fade), steps=10)


def render(t):
    anim.clear()
    a = 1 - smooth((t - T_FADE_OUT) / (CYCLE - T_FADE_OUT))   # fundido final
    draw_twinkle(clock)
    draw_heart(t, a)
    draw_inner(t, a)
    draw_message(t, a)
    draw_shooting_star(t, a)
    screen.update()


# ----------------------------------------------------------------------
# Bucle principal y controles
# ----------------------------------------------------------------------
def tick():
    global clock, last_tick
    if not running:
        return

    start = time.perf_counter()
    dt = min(start - last_tick, 0.1)   # evita saltos grandes
    last_tick = start

    if not paused:
        clock += dt
        render(clock % CYCLE)

    # Compensa el tiempo de dibujo para mantener ~FPS constantes.
    spent = int((time.perf_counter() - start) * 1000)
    try:
        screen.ontimer(tick, max(1, FRAME_MS - spent))
    except (turtle.Terminator, tkinter.TclError):
        pass


def toggle_pause():
    global paused
    paused = not paused


def close():
    global running
    running = False
    try:
        screen.bye()
    except (turtle.Terminator, tkinter.TclError):
        pass


def main():
    draw_static()
    screen.update()
    screen.listen()
    screen.onkey(toggle_pause, "space")
    screen.onkey(close, "Escape")
    screen.ontimer(tick, FRAME_MS)
    try:
        screen.mainloop()
    except (turtle.Terminator, tkinter.TclError):
        pass


if __name__ == "__main__":
    main()