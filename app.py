"""Bacho ki Drawing Book - ek hi file me (app + drawing engine).

Har seed par naye, original coloring pages banata hai.
Sirf Streamlit + Pillow use hota hai.
"""
import io
import math
import random

import streamlit as st
from PIL import Image, ImageDraw, ImageFont

W, H = 1240, 1754  # A4 @ 150 dpi
LW = 7
BLACK, WHITE = "black", "white"


# ----------------------------------------------------------------- helpers
def get_font(size):
    for name in ("DejaVuSans-Bold.ttf", "arialbd.ttf", "Arial Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size)
    except TypeError:
        return ImageFont.load_default()


def poly(d, pts):
    pts = list(pts)
    d.polygon(pts, fill=WHITE)
    d.line(pts + [pts[0]], fill=BLACK, width=LW, joint="curve")


def circ(d, x, y, r):
    d.ellipse([x - r, y - r, x + r, y + r], fill=WHITE, outline=BLACK, width=LW)


def dot(d, x, y, r):
    d.ellipse([x - r, y - r, x + r, y + r], fill=BLACK)


def ell(d, x0, y0, x1, y1):
    d.ellipse([x0, y0, x1, y1], fill=WHITE, outline=BLACK, width=LW)


def rect(d, x0, y0, x1, y1):
    d.rectangle([x0, y0, x1, y1], fill=WHITE, outline=BLACK, width=LW)


def blob(d, circles):
    """Kai gol shapes ka sirf bahari outline (badal, jhaadi, ped ka patta)."""
    for x, y, r in circles:
        d.ellipse([x - r - LW, y - r - LW, x + r + LW, y + r + LW], fill=BLACK)
    for x, y, r in circles:
        d.ellipse([x - r, y - r, x + r, y + r], fill=WHITE)


def rot_ellipse(cx, cy, a, b, ang, n=48):
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        x, y = a * math.cos(t), b * math.sin(t)
        pts.append((cx + x * math.cos(ang) - y * math.sin(ang),
                    cy + x * math.sin(ang) + y * math.cos(ang)))
    return pts


# ----------------------------------------------------------------- objects
# Sab ka signature: f(d, x, y, r, rng)
def flower(d, x, y, r, rng):
    tilt = rng.randint(-25, 25)
    d.line([(x, y), (x + tilt, y + r * 3.4)], fill=BLACK, width=LW + 2)
    poly(d, rot_ellipse(x + tilt * 0.5 + r * 0.8, y + r * 2.2, r * 0.6, r * 0.25, -0.5))
    n = rng.choice([5, 6, 7, 8])
    for i in range(n):
        a = 2 * math.pi * i / n
        poly(d, rot_ellipse(x + math.cos(a) * r, y + math.sin(a) * r, r * 0.75, r * 0.4, a))
    circ(d, x, y, r * 0.55)


def sun(d, x, y, r, rng):
    for i in range(12):
        a = 2 * math.pi * i / 12
        d.line([(x + math.cos(a) * (r + 15), y + math.sin(a) * (r + 15)),
                (x + math.cos(a) * (r + r * 0.55), y + math.sin(a) * (r + r * 0.55))],
               fill=BLACK, width=LW)
    circ(d, x, y, r)
    dot(d, x - r * 0.3, y - r * 0.15, r * 0.08)
    dot(d, x + r * 0.3, y - r * 0.15, r * 0.08)
    d.arc([x - r * 0.5, y - r * 0.4, x + r * 0.5, y + r * 0.55], 20, 160, fill=BLACK, width=LW)


def cloud(d, x, y, r, rng):
    s = r
    blob(d, [(x - s * 0.6, y, s * 0.5), (x, y - s * 0.3, s * 0.65),
             (x + s * 0.65, y, s * 0.5), (x, y + s * 0.1, s * 0.5)])


def house(d, x, g, s, rng):
    rect(d, x + s * 0.2, g - s * 1.15, x + s * 0.38, g - s * 0.7)  # chimney
    rect(d, x - s / 2, g - s * 0.7, x + s / 2, g)
    poly(d, [(x - s * 0.62, g - s * 0.7), (x, g - s * 1.2), (x + s * 0.62, g - s * 0.7)])
    rect(d, x - s * 0.1, g - s * 0.38, x + s * 0.1, g)
    dot(d, x + s * 0.06, g - s * 0.19, 5)
    for wx in (x - s * 0.38, x + s * 0.2):
        rect(d, wx, g - s * 0.58, wx + s * 0.18, g - s * 0.4)
        d.line([(wx + s * 0.09, g - s * 0.58), (wx + s * 0.09, g - s * 0.4)], fill=BLACK, width=LW - 2)
        d.line([(wx, g - s * 0.49), (wx + s * 0.18, g - s * 0.49)], fill=BLACK, width=LW - 2)


def tree(d, x, g, s, rng):
    rect(d, x - s * 0.1, g - s * 0.8, x + s * 0.1, g)
    blob(d, [(x, g - s * 1.1, s * 0.38), (x - s * 0.3, g - s * 0.85, s * 0.34),
             (x + s * 0.3, g - s * 0.85, s * 0.34)])
    for _ in range(3):  # phal
        circ(d, x + rng.randint(-int(s * 0.3), int(s * 0.3)),
             g - s * 1.0 + rng.randint(-int(s * 0.25), int(s * 0.2)), s * 0.05)


def butterfly(d, x, y, r, rng):
    poly(d, rot_ellipse(x - r * 0.55, y - r * 0.35, r * 0.6, r * 0.38, -0.6))
    poly(d, rot_ellipse(x + r * 0.55, y - r * 0.35, r * 0.6, r * 0.38, 0.6))
    poly(d, rot_ellipse(x - r * 0.4, y + r * 0.4, r * 0.42, r * 0.28, 0.5))
    poly(d, rot_ellipse(x + r * 0.4, y + r * 0.4, r * 0.42, r * 0.28, -0.5))
    circ(d, x - r * 0.6, y - r * 0.35, r * 0.12)
    circ(d, x + r * 0.6, y - r * 0.35, r * 0.12)
    ell(d, x - r * 0.09, y - r * 0.55, x + r * 0.09, y + r * 0.6)
    d.line([(x, y - r * 0.55), (x - r * 0.3, y - r * 0.95)], fill=BLACK, width=LW - 2)
    d.line([(x, y - r * 0.55), (x + r * 0.3, y - r * 0.95)], fill=BLACK, width=LW - 2)


def star(d, x, y, r, rng):
    pts = []
    for i in range(10):
        rr = r if i % 2 == 0 else r * 0.45
        a = -math.pi / 2 + i * math.pi / 5
        pts.append((x + rr * math.cos(a), y + rr * math.sin(a)))
    poly(d, pts)


def fish(d, x, y, r, rng):
    dr = rng.choice([-1, 1])
    poly(d, [(x - dr * r * 0.8, y), (x - dr * r * 1.5, y - r * 0.5), (x - dr * r * 1.5, y + r * 0.5)])
    poly(d, [(x - r * 0.2, y - r * 0.5), (x + r * 0.1, y - r * 0.95), (x + r * 0.4, y - r * 0.5)])
    ell(d, x - r, y - r * 0.55, x + r, y + r * 0.55)
    dot(d, x + dr * r * 0.55, y - r * 0.12, r * 0.08)
    d.line([(x + dr * r * 0.92, y + r * 0.12), (x + dr * r * 0.72, y + r * 0.2)], fill=BLACK, width=LW - 2)
    for k in (-1, 0, 1):
        bx = x + k * r * 0.28
        d.arc([bx - r * 0.2, y - r * 0.25, bx + r * 0.2, y + r * 0.25], 90, 270, fill=BLACK, width=LW - 2)


def bubble(d, x, y, r, rng):
    d.ellipse([x - r, y - r, x + r, y + r], outline=BLACK, width=LW - 1)
    d.arc([x - r * 0.6, y - r * 0.6, x + r * 0.1, y + r * 0.1], 200, 280, fill=BLACK, width=LW - 3)


def seaweed(d, x, base, h, rng):
    ph = rng.random() * 6
    left = [(x - 14 + math.sin(t * 6 + ph) * 30, base - t * h) for t in [i / 30 for i in range(31)]]
    right = [(px + 28, py) for px, py in left]
    d.line(left, fill=BLACK, width=LW, joint="curve")
    d.line(right, fill=BLACK, width=LW, joint="curve")
    d.line([left[-1], right[-1]], fill=BLACK, width=LW)
    for i in range(3, 28, 6):  # patte
        d.line([left[i], (left[i][0] - 35, left[i][1] - 20)], fill=BLACK, width=LW - 2)
        d.line([right[i], (right[i][0] + 35, right[i][1] - 20)], fill=BLACK, width=LW - 2)


def balloon(d, x, y, r, rng):
    d.line([(x + math.sin(i) * r * 0.12, y + r * 1.08 + i * r * 0.25) for i in range(8)],
           fill=BLACK, width=LW - 2, joint="curve")
    ell(d, x - r * 0.7, y - r, x + r * 0.7, y + r * 0.9)
    poly(d, [(x, y + r * 0.9), (x - r * 0.12, y + r * 1.08), (x + r * 0.12, y + r * 1.08)])
    d.arc([x - r * 0.5, y - r * 0.8, x - r * 0.1, y - r * 0.3], 180, 270, fill=BLACK, width=LW - 2)


def rocket(d, x, y, r, rng):
    poly(d, [(x - r * 0.2, y + r), (x, y + r * 1.6), (x + r * 0.2, y + r)])
    poly(d, [(x - r * 0.3, y + r * 0.2), (x - r * 0.8, y + r * 0.95), (x - r * 0.3, y + r * 0.7)])
    poly(d, [(x + r * 0.3, y + r * 0.2), (x + r * 0.8, y + r * 0.95), (x + r * 0.3, y + r * 0.7)])
    poly(d, rot_ellipse(x, y, r * 0.4, r, 0))
    circ(d, x, y - r * 0.2, r * 0.2)
    circ(d, x, y - r * 0.2, r * 0.1)
    d.line([(x - r * 0.38, y + r * 0.55), (x + r * 0.38, y + r * 0.55)], fill=BLACK, width=LW)


def cat(d, x, y, r, rng):
    poly(d, [(x - r * 0.85, y - r * 0.2), (x - r * 0.7, y - r * 1.1), (x - r * 0.15, y - r * 0.7)])
    poly(d, [(x + r * 0.85, y - r * 0.2), (x + r * 0.7, y - r * 1.1), (x + r * 0.15, y - r * 0.7)])
    ell(d, x - r, y - r * 0.8, x + r, y + r * 0.8)
    for sx in (-1, 1):
        ex = x + sx * r * 0.38
        ell(d, ex - r * 0.16, y - r * 0.25, ex + r * 0.16, y + r * 0.1)
        dot(d, ex, y - r * 0.08, r * 0.06)
        for k in range(3):
            yy = y + r * 0.28 + k * r * 0.1
            d.line([(x + sx * r * 0.4, yy), (x + sx * r * 0.95, yy + (k - 1) * r * 0.1)],
                   fill=BLACK, width=LW - 3)
    poly(d, [(x - r * 0.1, y + r * 0.2), (x + r * 0.1, y + r * 0.2), (x, y + r * 0.33)])
    d.arc([x - r * 0.25, y + r * 0.3, x, y + r * 0.55], 0, 180, fill=BLACK, width=LW - 2)
    d.arc([x, y + r * 0.3, x + r * 0.25, y + r * 0.55], 0, 180, fill=BLACK, width=LW - 2)


def owl(d, x, y, r, rng):
    poly(d, [(x - r * 0.6, y - r * 0.85), (x - r * 0.7, y - r * 1.25), (x - r * 0.25, y - r * 0.95)])
    poly(d, [(x + r * 0.6, y - r * 0.85), (x + r * 0.7, y - r * 1.25), (x + r * 0.25, y - r * 0.95)])
    ell(d, x - r * 0.8, y - r, x + r * 0.8, y + r)
    for sx in (-1, 1):
        circ(d, x + sx * r * 0.35, y - r * 0.35, r * 0.28)
        dot(d, x + sx * r * 0.35, y - r * 0.35, r * 0.1)
        d.arc([x + sx * r * 0.85 - r * 0.3, y - r * 0.1, x + sx * r * 0.85 + r * 0.3, y + r * 0.8],
              90 if sx < 0 else 270, 270 if sx < 0 else 450, fill=BLACK, width=LW - 1)
        d.line([(x + sx * r * 0.25, y + r), (x + sx * r * 0.25, y + r * 1.15)], fill=BLACK, width=LW)
    poly(d, [(x - r * 0.1, y - r * 0.1), (x + r * 0.1, y - r * 0.1), (x, y + r * 0.12)])
    for k in range(3):
        d.arc([x - r * 0.4, y + r * 0.15 + k * r * 0.22, x + r * 0.4, y + r * 0.5 + k * r * 0.22],
              20, 160, fill=BLACK, width=LW - 2)


def car(d, x, y, r, rng):
    poly(d, [(x - r * 0.55, y - r * 0.2), (x - r * 0.3, y - r * 0.7),
             (x + r * 0.35, y - r * 0.7), (x + r * 0.6, y - r * 0.2)])
    rect(d, x - r, y - r * 0.2, x + r, y + r * 0.4)
    poly(d, [(x - r * 0.42, y - r * 0.25), (x - r * 0.25, y - r * 0.6), (x - r * 0.03, y - r * 0.6),
             (x - r * 0.03, y - r * 0.25)])
    poly(d, [(x + r * 0.07, y - r * 0.25), (x + r * 0.07, y - r * 0.6), (x + r * 0.3, y - r * 0.6),
             (x + r * 0.45, y - r * 0.25)])
    for wx in (x - r * 0.55, x + r * 0.55):
        circ(d, wx, y + r * 0.4, r * 0.26)
        circ(d, wx, y + r * 0.4, r * 0.1)
    circ(d, x + r * 0.88, y + r * 0.05, r * 0.07)


def boat(d, x, y, r, rng):
    d.line([(x, y - r * 1.2), (x, y + r * 0.1)], fill=BLACK, width=LW)
    poly(d, [(x + r * 0.07, y - r * 1.1), (x + r * 0.85, y - r * 0.15), (x + r * 0.07, y - r * 0.15)])
    poly(d, [(x - r * 0.07, y - r * 0.9), (x - r * 0.6, y - r * 0.15), (x - r * 0.07, y - r * 0.15)])
    poly(d, [(x - r, y + r * 0.1), (x + r, y + r * 0.1), (x + r * 0.6, y + r * 0.6), (x - r * 0.6, y + r * 0.6)])
    circ(d, x, y + r * 0.35, r * 0.1)
    for k in (-1, 0, 1):
        d.arc([x + k * r * 0.7 - r * 0.3, y + r * 0.55, x + k * r * 0.7 + r * 0.3, y + r * 0.9],
              0, 180, fill=BLACK, width=LW - 2)


def apple(d, x, y, r, rng):
    d.line([(x, y - r * 0.4), (x + r * 0.1, y - r * 0.8)], fill=BLACK, width=LW)
    blob(d, [(x - r * 0.3, y, r * 0.55), (x + r * 0.3, y, r * 0.55), (x, y + r * 0.2, r * 0.55)])
    poly(d, rot_ellipse(x + r * 0.38, y - r * 0.68, r * 0.28, r * 0.12, -0.5))


def icecream(d, x, y, r, rng):
    poly(d, [(x - r * 0.4, y), (x + r * 0.4, y), (x, y + r * 1.1)])
    d.line([(x - r * 0.25, y + r * 0.2), (x + r * 0.15, y + r * 0.6)], fill=BLACK, width=LW - 3)
    d.line([(x + r * 0.25, y + r * 0.2), (x - r * 0.15, y + r * 0.6)], fill=BLACK, width=LW - 3)
    circ(d, x, y - r * 0.1, r * 0.45)
    circ(d, x, y - r * 0.65, r * 0.38)
    circ(d, x, y - r * 1.1, r * 0.12)


def heart(d, x, y, r, rng):
    pts = []
    for i in range(60):
        t = 2 * math.pi * i / 60
        hx = 16 * math.sin(t) ** 3
        hy = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((x + hx * r / 16, y - hy * r / 16))
    poly(d, pts)


def moon(d, x, y, r, rng):
    pts = [(x + r * math.cos(t), y + r * math.sin(t))
           for t in [math.pi / 2 + math.pi * i / 30 for i in range(31)]]
    pts += [(x - r * 0.45 * math.sin(s), y - r * math.cos(s))
            for s in [math.pi * i / 30 for i in range(31)]]
    poly(d, pts)
    star(d, x + r * 0.7, y - r * 0.3, r * 0.2, rng)


# ----------------------------------------------------------------- scenes
def scatter(d, rng, items, y0, y1, placed=None):
    """Items ko bina takraye random jagah par rakhta hai.
    items = [(func, size, placement_radius)]"""
    placed = list(placed or [])
    for func, size, pr in items:
        if y1 - pr < y0 + pr:
            continue
        for _ in range(400):
            x = rng.randint(pr + 50, W - pr - 50)
            y = rng.randint(y0 + pr, y1 - pr)
            if all(math.hypot(x - px, y - py) > pr + qr + 20 for px, py, qr in placed):
                placed.append((x, y, pr))
                func(d, x, y, size, rng)
                break


def garden(d, rng):
    g = 1020
    scatter(d, rng, [(sun, 110, 170), (cloud, 100, 130), (cloud, 90, 120),
                     (butterfly, 55, 70), (butterfly, 50, 65)], 190, 520)
    d.line([(x, g + math.sin(x / 90.0) * 14) for x in range(0, W + 1, 20)], fill=BLACK, width=LW)
    hx = rng.choice([340, 900])
    house(d, hx, g, 420, rng)
    tree(d, W - hx, g, 330, rng)
    for i in range(5):
        flower(d, 170 + i * 225, 1230 + rng.randint(-20, 60), rng.randint(45, 65), rng)


def sea(d, rng):
    d.line([(x, 215 + math.sin(x / 40.0) * 12) for x in range(0, W + 1, 10)], fill=BLACK, width=LW)
    items = [(fish, rng.randint(80, 120), 150) for _ in range(6)]
    items += [(bubble, rng.randint(20, 35), 40) for _ in range(6)]
    scatter(d, rng, items, 300, 1080)
    for i in range(4):
        seaweed(d, 150 + i * 300 + rng.randint(-40, 40), 1580, rng.randint(250, 400), rng)
    for _ in range(2):
        star(d, rng.randint(600, 1100), 1500, 45, rng)


def sky(d, rng):
    items = [(rocket, 140, 190)]
    items += [(balloon, rng.randint(80, 105), 140) for _ in range(5)]
    items += [(cloud, rng.randint(90, 115), 140) for _ in range(3)]
    items += [(star, rng.randint(40, 60), 70) for _ in range(7)]
    scatter(d, rng, items, 200, 1580)


def animals(d, rng):
    big = [(cat, 300), (owl, 270)]
    rng.shuffle(big)
    placed = []
    for (func, r), y in zip(big, (640, 1270)):
        func(d, W // 2, y, r, rng)
        placed.append((W // 2, y, r + 40))
    items = [(butterfly, 55, 75)] * 3 + [(star, 42, 55)] * 3 + [(flower, 38, 95)] * 2
    scatter(d, rng, items, 190, 1600, placed)


def vehicles(d, rng):
    items = [(car, rng.randint(110, 150), 190) for _ in range(3)]
    items += [(boat, rng.randint(100, 130), 170), (rocket, 120, 170)]
    items += [(cloud, rng.randint(80, 110), 130) for _ in range(2)]
    items += [(sun, 80, 130)] + [(star, rng.randint(35, 55), 65) for _ in range(3)]
    scatter(d, rng, items, 200, 1580)


def treats(d, rng):
    items = [(apple, rng.randint(90, 120), 130) for _ in range(3)]
    items += [(icecream, rng.randint(90, 115), 150) for _ in range(3)]
    items += [(heart, rng.randint(60, 90), 85) for _ in range(3)]
    items += [(butterfly, 55, 75)] * 2 + [(star, 45, 60)] * 3 + [(flower, 40, 100)] * 2
    scatter(d, rng, items, 200, 1560)


POOL = [(sun, 95, 150), (cloud, 95, 125), (butterfly, 60, 80), (star, 50, 62), (fish, 90, 135),
        (balloon, 90, 135), (rocket, 115, 165), (car, 110, 130), (boat, 100, 130), (apple, 90, 105),
        (icecream, 90, 125), (heart, 70, 80), (moon, 85, 95), (flower, 45, 100), (cat, 130, 150),
        (owl, 120, 150), (house, 200, 170), (tree, 180, 150)]


def surprise(d, rng):
    chosen = [rng.choice(POOL) for _ in range(rng.randint(9, 12))]
    chosen.sort(key=lambda t: -t[2])
    items = []
    for f, s, pr in chosen:
        k = rng.uniform(0.85, 1.2)
        items.append((f, int(s * k), int(pr * k)))
    scatter(d, rng, items, 200, 1580)


def mandala(d, rng):
    cx, cy = W // 2, H // 2 + 20
    rings = rng.randint(5, 6)
    for k in range(rings):
        dist = 520 - k * 80
        n = rng.choice([8, 10, 12, 16, 20])
        off = rng.random()
        la = 70
        lb = max(12, min(40, math.pi * dist / n * 0.45))
        for i in range(n):
            a = 2 * math.pi * i / n + off
            poly(d, rot_ellipse(cx + math.cos(a) * dist, cy + math.sin(a) * dist, la, lb, a))
        d.ellipse([cx - dist + 25, cy - dist + 25, cx + dist - 25, cy + dist - 25],
                  fill=WHITE, outline=BLACK, width=LW - 2)
    circ(d, cx, cy, 60)
    circ(d, cx, cy, 25)


THEMES = {
    "Bagicha (Garden)": garden,
    "Samundar (Sea)": sea,
    "Aasman (Sky)": sky,
    "Janwar (Animals)": animals,
    "Gaadiyan (Vehicles)": vehicles,
    "Mazedaar (Treats)": treats,
    "Surprise (Sab kuch)": surprise,
    "Mandala": mandala,
}


# ----------------------------------------------------------------- pages / book
def make_page(theme, seed, number):
    rng = random.Random(seed)
    img = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    THEMES[theme](d, rng)
    d.rectangle([0, 0, W, 175], fill=WHITE)
    d.text((W // 2, 85), f"Rang Bharo!  #{number}", fill=BLACK, font=get_font(72), anchor="mm")
    d.rectangle([0, H - 140, W, H], fill=WHITE)
    d.text((90, H - 70), "Naam: ____________________", fill=BLACK, font=get_font(44), anchor="lm")
    return img


def to_png(img):
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def generate_book(seed, themes, n_pages):
    """(png_bytes_list, pdf_bytes) lautata hai. Har seed = naya book."""
    themes = list(themes) or list(THEMES)
    rng = random.Random(seed)
    order = themes[:]
    rng.shuffle(order)
    images = [make_page(order[i % len(order)], rng.randrange(10 ** 9), i + 1) for i in range(n_pages)]
    buf = io.BytesIO()
    images[0].save(buf, "PDF", resolution=150.0, save_all=True, append_images=images[1:])
    return [to_png(im) for im in images], buf.getvalue()


# ----------------------------------------------------------------- Streamlit app
st.set_page_config(page_title="Drawing Book", page_icon="🎨", layout="wide")

st.title("🎨 Bacho ki Drawing Book")
st.write("Har baar naya drawing book! Download karo, print karo aur rang bharo. 🖍️")

with st.sidebar:
    st.header("Settings")
    n_pages = st.slider("Kitne pages?", 1, 12, 4)
    chosen = st.multiselect("Kaunse themes?", list(THEMES), default=list(THEMES))

st.button("🔄 Naya Drawing Book Do", type="primary")

# Har run (page kholna, button dabana, download karna) par bilkul naya seed,
# isliye har baar naye drawings aate hain.
seed = random.SystemRandom().randrange(10 ** 9)


@st.cache_data(show_spinner="Drawing book ban rahi hai... ✏️", max_entries=10)
def build(seed, n, themes):
    return generate_book(seed, list(themes), n)


pngs, pdf = build(seed, n_pages, tuple(chosen or THEMES))

st.download_button(
    "📄 Poori book PDF me download karo",
    data=pdf,
    file_name=f"drawing_book_{seed}.pdf",
    mime="application/pdf",
)

cols = st.columns(2)
for i, png in enumerate(pngs):
    with cols[i % 2]:
        st.image(png, caption=f"Page {i + 1}")
        st.download_button(
            f"⬇️ Page {i + 1} download",
            data=png,
            file_name=f"drawing_{seed}_{i + 1}.png",
            mime="image/png",
            key=f"dl_{seed}_{i}",
        )
