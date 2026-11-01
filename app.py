"""Bacho ki Drawing Book - ek hi file me (app + drawing engine).

* 1,000,000,000 (1 arab) alag-alag sheets: har sheet number ki sheet hamesha wahi rehti hai.
* Smooth lines (2x render), pyare chehre, frame, 10 themes.
* Sirf Streamlit + Pillow.
"""
import glob
import io
import math
import os
import random
from functools import lru_cache

import cv2
import numpy as np
import streamlit as st
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps, features

W, H = 1240, 1754  # A4 @ 150 dpi
S = 2               # supersampling: 2x me banake chhota karte hain -> smooth lines
LW = 7
BLACK, WHITE = "black", "white"
TOTAL = 1_000_000_000


# ----------------------------------------------------------------- canvas
@lru_cache(maxsize=32)
def get_font(size):
    size = int(size)
    for name in ("DejaVuSans-Bold.ttf", "arialbd.ttf", "Arial Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


class Canvas:
    """ImageDraw jaisa, par har coordinate/width ko S se guna karta hai."""

    def __init__(self, s=S):
        self.s = s
        self.img = Image.new("RGB", (W * s, H * s), WHITE)
        self.d = ImageDraw.Draw(self.img)

    def _xy(self, xy):
        s = self.s
        xy = list(xy)
        if xy and isinstance(xy[0], (tuple, list)):
            return [(x * s, y * s) for x, y in xy]
        return [v * s for v in xy]

    def _w(self, w):
        return max(1, int(round(w * self.s)))

    def line(self, xy, fill=None, width=1, joint=None):
        self.d.line(self._xy(xy), fill=fill, width=self._w(width), joint=joint)

    def polygon(self, xy, fill=None, outline=None):
        self.d.polygon(self._xy(xy), fill=fill, outline=outline)

    def ellipse(self, xy, fill=None, outline=None, width=1):
        self.d.ellipse(self._xy(xy), fill=fill, outline=outline, width=self._w(width))

    def arc(self, xy, start, end, fill=None, width=1):
        self.d.arc(self._xy(xy), start, end, fill=fill, width=self._w(width))

    def rectangle(self, xy, fill=None, outline=None, width=1):
        self.d.rectangle(self._xy(xy), fill=fill, outline=outline, width=self._w(width))

    def rounded_rectangle(self, xy, radius, fill=None, outline=None, width=1):
        self.d.rounded_rectangle(self._xy(xy), radius=radius * self.s, fill=fill,
                                 outline=outline, width=self._w(width))

    def text(self, xy, text, fill, size, anchor="mm", font=None, stroke=0):
        """font = size -> ImageFont function (default: get_font). stroke>0 => khokhla (hollow) text."""
        kw = {}
        if stroke:
            kw = dict(stroke_width=int(stroke * self.s), stroke_fill=BLACK)
        self.d.text((xy[0] * self.s, xy[1] * self.s), text, fill=fill,
                    font=(font or get_font)(size * self.s), anchor=anchor, **kw)


# ----------------------------------------------------------------- helpers
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


def dome(cx, cy, rx, ry, n=30):
    """Upar ka aadha ellipse (topi, gumbad)."""
    return [(cx + rx * math.cos(math.pi * i / n), cy - ry * math.sin(math.pi * i / n))
            for i in range(n + 1)]


def face(d, x, y, r):
    """Pyara chehra: aankhein, muskaan, gaal."""
    if r < 38:
        return
    e = max(3, r * 0.07)
    dot(d, x - r * 0.3, y - r * 0.1, e)
    dot(d, x + r * 0.3, y - r * 0.1, e)
    d.arc([x - r * 0.28, y - r * 0.05, x + r * 0.28, y + r * 0.45], 20, 160, fill=BLACK, width=4)
    if r >= 60:
        for sx in (-1, 1):
            cx = x + sx * r * 0.58
            d.ellipse([cx - r * 0.11, y + r * 0.1, cx + r * 0.11, y + r * 0.24], outline=BLACK, width=2)


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
    if rng.random() < 0.5:
        circ(d, x, y, r * 0.25)


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
    face(d, x, y + s * 0.05, s * 0.7)


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


def house_c(d, x, y, s, rng):  # center-based (surprise pool ke liye)
    house(d, x, y + s * 0.45, s, rng)


def tree_c(d, x, y, s, rng):
    tree(d, x, y + s * 0.6, s, rng)


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
    face(d, x, y + r * 0.05, r * 0.7)


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
    face(d, x + r * 0.05, y - r * 0.05, r * 0.7)


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
    face(d, x, y + r * 0.1, r * 0.75)


def icecream(d, x, y, r, rng):
    poly(d, [(x - r * 0.4, y), (x + r * 0.4, y), (x, y + r * 1.1)])
    d.line([(x - r * 0.25, y + r * 0.2), (x + r * 0.15, y + r * 0.6)], fill=BLACK, width=LW - 3)
    d.line([(x + r * 0.25, y + r * 0.2), (x - r * 0.15, y + r * 0.6)], fill=BLACK, width=LW - 3)
    circ(d, x, y - r * 0.1, r * 0.45)
    circ(d, x, y - r * 0.65, r * 0.38)
    circ(d, x, y - r * 1.1, r * 0.12)
    face(d, x, y - r * 0.05, r * 0.5)


def heart(d, x, y, r, rng):
    pts = []
    for i in range(60):
        t = 2 * math.pi * i / 60
        hx = 16 * math.sin(t) ** 3
        hy = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((x + hx * r / 16, y - hy * r / 16))
    poly(d, pts)
    face(d, x, y - r * 0.05, r * 0.7)


def moon(d, x, y, r, rng):
    pts = [(x + r * math.cos(t), y + r * math.sin(t))
           for t in [math.pi / 2 + math.pi * i / 30 for i in range(31)]]
    pts += [(x - r * 0.45 * math.sin(s), y - r * math.cos(s))
            for s in [math.pi * i / 30 for i in range(31)]]
    poly(d, pts)
    star(d, x + r * 0.7, y - r * 0.3, r * 0.2, rng)


# ---- naye objects
def ladybug(d, x, y, r, rng):
    for sy in (-0.3, 0.15, 0.6):
        for sx in (-1, 1):
            d.line([(x + sx * r * 0.85, y + sy * r), (x + sx * r * 1.2, y + sy * r + r * 0.12)],
                   fill=BLACK, width=LW)
    ell(d, x - r, y - r * 0.75, x + r, y + r * 0.95)
    poly(d, rot_ellipse(x, y - r * 0.8, r * 0.55, r * 0.38, 0))
    d.line([(x, y - r * 0.42), (x, y + r * 0.95)], fill=BLACK, width=LW)
    for sx, sy, sr in [(-0.5, -0.05, 0.2), (0.5, -0.05, 0.2), (-0.45, 0.5, 0.16), (0.45, 0.5, 0.16)]:
        circ(d, x + sx * r, y + sy * r, sr * r)
    for sx in (-1, 1):
        dot(d, x + sx * r * 0.2, y - r * 0.85, max(3, r * 0.06))
        d.line([(x + sx * r * 0.2, y - r * 1.15), (x + sx * r * 0.45, y - r * 1.5)], fill=BLACK, width=LW - 2)
        dot(d, x + sx * r * 0.45, y - r * 1.5, max(4, r * 0.07))


def mushroom(d, x, y, r, rng):
    poly(d, [(x - r * 0.32, y), (x + r * 0.32, y), (x + r * 0.42, y + r * 0.95), (x - r * 0.42, y + r * 0.95)])
    poly(d, dome(x, y, r, r * 0.9))
    for dx, dy, rr in [(-0.45, -0.4, 0.17), (0.1, -0.62, 0.2), (0.5, -0.28, 0.14)]:
        circ(d, x + dx * r, y + dy * r, rr * r)
    face(d, x, y + r * 0.5, r * 0.5)


def cupcake(d, x, y, r, rng):
    poly(d, [(x - r * 0.7, y), (x + r * 0.7, y), (x + r * 0.5, y + r * 0.9), (x - r * 0.5, y + r * 0.9)])
    for k in (-0.35, 0, 0.35):
        d.line([(x + k * r * 0.9, y + r * 0.2), (x + k * r * 0.65, y + r * 0.9)], fill=BLACK, width=LW - 3)
    blob(d, [(x - r * 0.45, y - r * 0.2, r * 0.4), (x + r * 0.45, y - r * 0.2, r * 0.4),
             (x, y - r * 0.55, r * 0.45)])
    circ(d, x, y - r * 1.12, r * 0.14)
    for _ in range(4):
        sx = rng.uniform(-0.55, 0.55)
        sy = rng.uniform(-0.55, -0.1)
        d.line([(x + sx * r, y + sy * r), (x + sx * r + r * 0.1, y + sy * r + r * 0.06)],
               fill=BLACK, width=LW - 2)
    face(d, x, y + r * 0.45, r * 0.5)


def turtle(d, x, y, r, rng):
    dr = rng.choice([-1, 1])
    ell(d, x - r * 0.75, y + r * 0.35, x - r * 0.3, y + r * 0.78)
    ell(d, x + r * 0.3, y + r * 0.35, x + r * 0.75, y + r * 0.78)
    poly(d, [(x - dr * r * 0.9, y + r * 0.1), (x - dr * r * 1.3, y + r * 0.22), (x - dr * r * 0.9, y + r * 0.32)])
    hx = x + dr * r * 1.0
    circ(d, hx, y - r * 0.05, r * 0.3)
    dot(d, hx + dr * r * 0.1, y - r * 0.12, max(3, r * 0.045))
    d.arc([hx - r * 0.05, y - r * 0.05, hx + r * 0.2, y + r * 0.15], 20, 160, fill=BLACK, width=LW - 3)
    poly(d, dome(x, y + r * 0.45, r, r * 0.95))
    circ(d, x, y - r * 0.05, r * 0.22)
    circ(d, x - r * 0.5, y + r * 0.2, r * 0.16)
    circ(d, x + r * 0.5, y + r * 0.2, r * 0.16)


def duck(d, x, y, r, rng):
    poly(d, [(x - r * 0.85, y + r * 0.05), (x - r * 1.35, y - r * 0.25), (x - r * 0.7, y + r * 0.35)])
    for fx in (-0.2, 0.3):
        d.line([(x + fx * r, y + r * 0.85), (x + fx * r, y + r * 1.05)], fill=BLACK, width=LW)
        d.line([(x + fx * r - r * 0.12, y + r * 1.05), (x + fx * r + r * 0.12, y + r * 1.05)],
               fill=BLACK, width=LW)
    ell(d, x - r, y - r * 0.05, x + r * 0.85, y + r * 0.85)
    circ(d, x + r * 0.5, y - r * 0.55, r * 0.45)
    poly(d, [(x + r * 0.9, y - r * 0.6), (x + r * 1.45, y - r * 0.48), (x + r * 0.9, y - r * 0.35)])
    dot(d, x + r * 0.62, y - r * 0.7, max(3, r * 0.06))
    d.arc([x - r * 0.7, y + r * 0.0, x + r * 0.2, y + r * 0.65], 0, 180, fill=BLACK, width=LW - 1)


def rabbit(d, x, y, r, rng):
    for sx in (-1, 1):
        ell(d, x + sx * r * 0.35 - r * 0.2, y - r * 1.75, x + sx * r * 0.35 + r * 0.2, y - r * 0.35)
        d.ellipse([x + sx * r * 0.35 - r * 0.09, y - r * 1.5, x + sx * r * 0.35 + r * 0.09, y - r * 0.6],
                  outline=BLACK, width=3)
    ell(d, x - r * 0.75, y + r * 0.35, x + r * 0.75, y + r * 1.55)
    d.ellipse([x - r * 0.4, y + r * 0.65, x + r * 0.4, y + r * 1.4], outline=BLACK, width=4)
    for sx in (-1, 1):
        ell(d, x + sx * r * 0.45 - r * 0.28, y + r * 1.45, x + sx * r * 0.45 + r * 0.28, y + r * 1.7)
    ell(d, x - r * 0.7, y - r * 0.6, x + r * 0.7, y + r * 0.55)
    for sx in (-1, 1):
        dot(d, x + sx * r * 0.28, y - r * 0.12, max(3, r * 0.07))
        for k in (-1, 1):
            d.line([(x + sx * r * 0.3, y + r * 0.2 + k * r * 0.03),
                    (x + sx * r * 0.85, y + r * 0.2 + k * r * 0.12)], fill=BLACK, width=3)
    poly(d, [(x - r * 0.09, y + r * 0.05), (x + r * 0.09, y + r * 0.05), (x, y + r * 0.17)])
    d.arc([x - r * 0.2, y + r * 0.14, x, y + r * 0.34], 0, 180, fill=BLACK, width=4)
    d.arc([x, y + r * 0.14, x + r * 0.2, y + r * 0.34], 0, 180, fill=BLACK, width=4)


def rainbow(d, x, y, r, rng):
    n = 5
    gap = r * 0.14
    for k in range(n):
        rr = r - k * gap
        d.arc([x - rr, y - rr, x + rr, y + rr], 180, 360, fill=BLACK, width=LW)
    inner = r - (n - 1) * gap
    d.line([(x - r, y), (x - inner, y)], fill=BLACK, width=LW)
    d.line([(x + inner, y), (x + r, y)], fill=BLACK, width=LW)
    cloud(d, x - r * 0.92, y + r * 0.02, r * 0.3, rng)
    cloud(d, x + r * 0.92, y + r * 0.02, r * 0.3, rng)


def rainbow_c(d, x, y, r, rng):
    rainbow(d, x, y + r * 0.35, r, rng)


def kite(d, x, y, r, rng):
    pts = [(x + math.sin(i * 1.2) * r * 0.18, y + r * 1.2 + i * r * 0.22) for i in range(7)]
    d.line(pts, fill=BLACK, width=LW - 2, joint="curve")
    for i in (2, 4, 6):
        bx, by = pts[i]
        poly(d, [(bx, by), (bx - r * 0.18, by - r * 0.1), (bx - r * 0.18, by + r * 0.1)])
        poly(d, [(bx, by), (bx + r * 0.18, by - r * 0.1), (bx + r * 0.18, by + r * 0.1)])
    poly(d, [(x, y - r), (x + r * 0.7, y), (x, y + r * 1.2), (x - r * 0.7, y)])
    d.line([(x, y - r), (x, y + r * 1.2)], fill=BLACK, width=LW - 2)
    d.line([(x - r * 0.7, y), (x + r * 0.7, y)], fill=BLACK, width=LW - 2)


# ----------------------------------------------------------------- scenes
def scatter(d, rng, items, y0, y1, placed=None):
    """Items ko bina takraye random jagah par rakhta hai. Placed list lautata hai.
    items = [(func, size, placement_radius)]"""
    placed = list(placed or [])
    for func, size, pr in items:
        if y1 - pr < y0 + pr:
            continue
        for _ in range(400):
            x = rng.randint(pr + 55, W - pr - 55)
            y = rng.randint(y0 + pr, y1 - pr)
            if all(math.hypot(x - px, y - py) > pr + qr + 20 for px, py, qr in placed):
                placed.append((x, y, pr))
                func(d, x, y, size, rng)
                break
    return placed


def sprinkle(d, rng, placed, y0=200, y1=1580, count=10):
    """Khali jagah me chhote taare/dil/bubbles bhar deta hai."""
    items = []
    for _ in range(count):
        f = rng.choice([star, heart, bubble])
        s = rng.randint(24, 34)
        items.append((f, s, s + 8))
    return scatter(d, rng, items, y0, y1, placed)


def garden(d, rng):
    g = rng.randint(980, 1060)
    placed = scatter(d, rng, [(sun, 110, 170), (cloud, 100, 130), (cloud, 90, 120),
                              (butterfly, 55, 70), (butterfly, 50, 65)], 190, 500)
    sprinkle(d, rng, placed, 190, 500, 5)
    # baad (fence)
    for x in range(60, W - 40, 66):
        poly(d, [(x, g), (x, g - 120), (x + 22, g - 148), (x + 44, g - 120), (x + 44, g)])
    for yy in (g - 95, g - 40):
        d.line([(60, yy), (W - 60, yy)], fill=BLACK, width=LW - 2)
    d.line([(x, g + math.sin(x / 90.0) * 14) for x in range(0, W + 1, 20)], fill=BLACK, width=LW)
    for x in range(70, W - 60, rng.randint(95, 140)):
        gy = g + math.sin(x / 90.0) * 14
        for ddx in (-12, 0, 12):
            d.line([(x, gy + 22), (x + ddx, gy + 22 - 30 + abs(ddx) * 0.3)], fill=BLACK, width=LW - 3)
    hx = rng.choice([300, 340, 900, 940])
    house(d, hx, g, rng.randint(380, 450), rng)
    tree(d, W - hx, g, rng.randint(290, 350), rng)
    n = rng.randint(5, 6)
    for i in range(n):
        flower(d, 150 + i * (W - 300) / (n - 1), 1240 + rng.randint(-20, 50), rng.randint(44, 64), rng)


def sea(d, rng):
    d.line([(x, 215 + math.sin(x / 40.0) * 12) for x in range(0, W + 1, 10)], fill=BLACK, width=LW)
    d.line([(x, 250 + math.sin(x / 55.0 + 1) * 10) for x in range(0, W + 1, 10)], fill=BLACK, width=LW - 3)
    items = [(turtle, rng.randint(85, 105), 150)]
    items += [(fish, rng.randint(80, 120), 150) for _ in range(rng.randint(5, 7))]
    items += [(bubble, rng.randint(20, 35), 40) for _ in range(6)]
    placed = scatter(d, rng, items, 300, 1080)
    sprinkle(d, rng, placed, 300, 1080, 6)
    for i in range(4):
        seaweed(d, 150 + i * 300 + rng.randint(-40, 40), 1580, rng.randint(250, 400), rng)
    for _ in range(2):
        star(d, rng.randint(600, 1100), 1500, 45, rng)


def sky(d, rng):
    items = [(rocket, 140, 190)]
    items += [(balloon, rng.randint(80, 105), 140) for _ in range(rng.randint(4, 5))]
    items += [(cloud, rng.randint(90, 115), 140) for _ in range(3)]
    items += [(kite, rng.randint(85, 105), 150) for _ in range(2)]
    items += [(star, rng.randint(40, 60), 70) for _ in range(5)]
    placed = scatter(d, rng, items, 200, 1580)
    sprinkle(d, rng, placed, 200, 1580, 8)


ANIMALS = [(cat, 1.0), (owl, 0.9), (rabbit, 0.62), (duck, 0.8), (turtle, 0.9)]


def animals(d, rng):
    """Ek bada janwar + uske niche naam (English aur Hindi)."""
    func, sz, en, hi = rng.choice(ANIMALS_NAMED)
    k = 2.0
    func(d, W // 2, 740, int(sz * k), rng)
    d.text((W // 2, 1160), en, BLACK, 104)
    if HAS_HINDI:
        d.text((W // 2, 1285), hi, BLACK, 112, font=get_hindi_font)
    placed = [(W // 2, 740, 400)] + [(W // 2 + dx, yy, 125) for dx in (-230, 0, 230) for yy in (1160, 1285)]
    items = [(butterfly, 55, 75)] * 2 + [(star, 42, 55)] * 3 + [(flower, 38, 95)] * 2
    placed = scatter(d, rng, items, 190, 1600, placed)
    sprinkle(d, rng, placed, 190, 1600, 8)


# ---- gaadiyan (Vehicles theme ke liye)
def bus(d, x, y, r, rng):
    rect(d, x - r, y - r * 0.5, x + r, y + r * 0.4)
    for i in range(5):
        wx = x - r * 0.92 + i * r * 0.33
        rect(d, wx, y - r * 0.4, wx + r * 0.25, y - r * 0.1)
    rect(d, x + r * 0.72, y - r * 0.4, x + r * 0.92, y + r * 0.4)
    d.line([(x + r * 0.82, y - r * 0.4), (x + r * 0.82, y + r * 0.4)], fill=BLACK, width=LW - 3)
    d.line([(x - r, y + r * 0.12), (x + r * 0.72, y + r * 0.12)], fill=BLACK, width=LW - 3)
    for wx in (x - r * 0.6, x + r * 0.45):
        circ(d, wx, y + r * 0.4, r * 0.22)
        circ(d, wx, y + r * 0.4, r * 0.09)
    circ(d, x - r * 0.9, y + r * 0.27, r * 0.05)


def truck(d, x, y, r, rng):
    rect(d, x - r, y - r * 0.6, x + r * 0.25, y + r * 0.35)
    poly(d, [(x + r * 0.3, y - r * 0.3), (x + r * 0.65, y - r * 0.3), (x + r, y + r * 0.05),
             (x + r, y + r * 0.35), (x + r * 0.3, y + r * 0.35)])
    poly(d, [(x + r * 0.4, y - r * 0.22), (x + r * 0.62, y - r * 0.22), (x + r * 0.82, y + r * 0.02),
             (x + r * 0.4, y + r * 0.02)])
    d.line([(x - r * 0.9, y - r * 0.2), (x + r * 0.15, y - r * 0.2)], fill=BLACK, width=LW - 3)
    for wx in (x - r * 0.7, x - r * 0.3, x + r * 0.62):
        circ(d, wx, y + r * 0.38, r * 0.2)
        circ(d, wx, y + r * 0.38, r * 0.08)
    circ(d, x + r * 0.93, y + r * 0.15, r * 0.05)


def firetruck(d, x, y, r, rng):
    rect(d, x - r, y - r * 0.25, x + r * 0.3, y + r * 0.4)
    poly(d, [(x + r * 0.35, y - r * 0.35), (x + r * 0.7, y - r * 0.35), (x + r, y), (x + r, y + r * 0.4),
             (x + r * 0.35, y + r * 0.4)])
    poly(d, [(x + r * 0.45, y - r * 0.27), (x + r * 0.66, y - r * 0.27), (x + r * 0.84, y - r * 0.03),
             (x + r * 0.45, y - r * 0.03)])
    rect(d, x - r * 0.9, y - r * 0.5, x + r * 0.2, y - r * 0.25)
    for k in range(7):
        lx = x - r * 0.82 + k * r * 0.15
        d.line([(lx, y - r * 0.5), (lx, y - r * 0.25)], fill=BLACK, width=LW - 3)
    circ(d, x + r * 0.5, y - r * 0.45, r * 0.09)
    d.line([(x - r * 0.9, y + r * 0.08), (x + r * 0.2, y + r * 0.08)], fill=BLACK, width=LW - 3)
    for wx in (x - r * 0.6, x - r * 0.15, x + r * 0.65):
        circ(d, wx, y + r * 0.43, r * 0.2)
        circ(d, wx, y + r * 0.43, r * 0.08)


def ambulance(d, x, y, r, rng):
    rect(d, x - r, y - r * 0.55, x + r * 0.45, y + r * 0.4)
    poly(d, [(x + r * 0.5, y - r * 0.3), (x + r * 0.72, y - r * 0.3), (x + r, y + r * 0.05),
             (x + r, y + r * 0.4), (x + r * 0.5, y + r * 0.4)])
    poly(d, [(x + r * 0.58, y - r * 0.22), (x + r * 0.7, y - r * 0.22), (x + r * 0.85, y - r * 0.0),
             (x + r * 0.58, y - r * 0.0)])
    a, b = r * 0.3, r * 0.1
    cx, cy = x - r * 0.3, y - r * 0.08
    poly(d, [(cx - b, cy - a), (cx + b, cy - a), (cx + b, cy - b), (cx + a, cy - b), (cx + a, cy + b),
             (cx + b, cy + b), (cx + b, cy + a), (cx - b, cy + a), (cx - b, cy + b), (cx - a, cy + b),
             (cx - a, cy - b), (cx - b, cy - b)])
    rect(d, x + r * 0.1, y - r * 0.7, x + r * 0.3, y - r * 0.55)
    for wx in (x - r * 0.55, x + r * 0.65):
        circ(d, wx, y + r * 0.4, r * 0.2)
        circ(d, wx, y + r * 0.4, r * 0.08)


def train(d, x, y, r, rng):
    y += r * 0.3
    rect(d, x - r, y - r * 0.75, x - r * 0.3, y + r * 0.35)
    rect(d, x - r * 1.08, y - r * 0.85, x - r * 0.22, y - r * 0.75)
    rect(d, x - r * 0.85, y - r * 0.6, x - r * 0.45, y - r * 0.2)
    rect(d, x - r * 0.3, y - r * 0.35, x + r * 0.75, y + r * 0.35)
    poly(d, [(x + r * 0.28, y - r * 0.35), (x + r * 0.2, y - r * 0.75), (x + r * 0.5, y - r * 0.75),
             (x + r * 0.42, y - r * 0.35)])
    poly(d, dome(x - r * 0.02, y - r * 0.35, r * 0.15, r * 0.2))
    poly(d, [(x + r * 0.75, y - r * 0.1), (x + r, y + r * 0.35), (x + r * 0.75, y + r * 0.35)])
    circ(d, x + r * 0.55, y - r * 0.1, r * 0.07)
    circ(d, x - r * 0.65, y + r * 0.4, r * 0.3)
    circ(d, x - r * 0.65, y + r * 0.4, r * 0.1)
    for wx in (x + r * 0.0, x + r * 0.5):
        circ(d, wx, y + r * 0.45, r * 0.22)
        circ(d, wx, y + r * 0.45, r * 0.08)
    d.line([(x - r * 0.65, y + r * 0.4), (x + r * 0.5, y + r * 0.45)], fill=BLACK, width=LW - 3)
    circ(d, x + r * 0.35, y - r * 0.95, r * 0.1)
    circ(d, x + r * 0.5, y - r * 1.22, r * 0.14)


def airplane(d, x, y, r, rng):
    poly(d, [(x - r * 0.8, y - r * 0.1), (x - r * 1.05, y - r * 0.65), (x - r * 0.75, y - r * 0.65),
             (x - r * 0.4, y - r * 0.1)])
    poly(d, [(x - r * 0.15, y + r * 0.1), (x - r * 0.55, y + r * 0.7), (x - r * 0.3, y + r * 0.7),
             (x + r * 0.3, y + r * 0.1)])
    ell(d, x - r, y - r * 0.22, x + r, y + r * 0.22)
    for i in range(6):
        circ(d, x - r * 0.45 + i * r * 0.17, y - r * 0.04, r * 0.045)
    poly(d, [(x + r * 0.62, y - r * 0.17), (x + r * 0.85, y - r * 0.05), (x + r * 0.62, y - r * 0.05)])
    ell(d, x - r * 0.2, y + r * 0.22, x + r * 0.15, y + r * 0.36)


def helicopter(d, x, y, r, rng):
    x += r * 0.15
    poly(d, [(x - r * 0.5, y - r * 0.1), (x - r * 1.2, y - r * 0.2), (x - r * 1.2, y - r * 0.05),
             (x - r * 0.5, y + r * 0.15)])
    poly(d, [(x - r * 1.2, y - r * 0.2), (x - r * 1.3, y - r * 0.55), (x - r * 1.08, y - r * 0.2)])
    ell(d, x - r * 1.33, y - r * 0.2, x - r * 1.17, y + r * 0.15)
    ell(d, x - r * 0.65, y - r * 0.5, x + r * 0.7, y + r * 0.4)
    poly(d, rot_ellipse(x + r * 0.35, y - r * 0.12, r * 0.28, r * 0.22, -0.2))
    d.line([(x - r * 0.1, y - r * 0.45), (x - r * 0.1, y + r * 0.35)], fill=BLACK, width=LW - 3)
    d.line([(x, y - r * 0.5), (x, y - r * 0.72)], fill=BLACK, width=LW)
    ell(d, x - r * 0.95, y - r * 0.8, x + r * 0.95, y - r * 0.68)
    for sx in (x - r * 0.3, x + r * 0.3):
        d.line([(sx, y + r * 0.38), (sx, y + r * 0.65)], fill=BLACK, width=LW)
    d.line([(x - r * 0.55, y + r * 0.65), (x + r * 0.65, y + r * 0.65)], fill=BLACK, width=LW + 2)


def bicycle(d, x, y, r, rng):
    wr = r * 0.42
    rear, front = (x - r * 0.55, y + r * 0.3), (x + r * 0.55, y + r * 0.3)
    for cx, cy in (rear, front):
        circ(d, cx, cy, wr)
        circ(d, cx, cy, wr * 0.18)
        for k in range(8):
            a = math.pi * k / 4
            d.line([(cx, cy), (cx + math.cos(a) * wr, cy + math.sin(a) * wr)], fill=BLACK, width=2)
    seat, ped, head = (x - r * 0.2, y - r * 0.2), (x, y + r * 0.3), (x + r * 0.4, y - r * 0.25)
    for a, b in ((rear, seat), (seat, ped), (ped, rear), (seat, head), (ped, head), (head, front)):
        d.line([a, b], fill=BLACK, width=LW)
    d.line([(x + r * 0.4, y - r * 0.25), (x + r * 0.34, y - r * 0.5), (x + r * 0.55, y - r * 0.5)],
           fill=BLACK, width=LW, joint="curve")
    d.line([(x - r * 0.35, y - r * 0.24), (x - r * 0.05, y - r * 0.24)], fill=BLACK, width=LW + 4)
    circ(d, x, y + r * 0.3, r * 0.08)


def motorcycle(d, x, y, r, rng):
    for cx in (x - r * 0.6, x + r * 0.6):
        circ(d, cx, y + r * 0.3, r * 0.4)
        circ(d, cx, y + r * 0.3, r * 0.15)
    poly(d, [(x - r * 0.5, y + r * 0.2), (x - r * 0.4, y - r * 0.15), (x + r * 0.1, y - r * 0.2),
             (x + r * 0.35, y), (x + r * 0.35, y + r * 0.3), (x - r * 0.2, y + r * 0.3)])
    ell(d, x - r * 0.1, y - r * 0.45, x + r * 0.35, y - r * 0.15)
    poly(d, [(x - r * 0.6, y - r * 0.2), (x - r * 0.1, y - r * 0.2), (x - r * 0.1, y - r * 0.08),
             (x - r * 0.6, y - r * 0.08)])
    d.line([(x + r * 0.45, y - r * 0.3), (x + r * 0.6, y + r * 0.3)], fill=BLACK, width=LW)
    d.line([(x + r * 0.42, y - r * 0.3), (x + r * 0.3, y - r * 0.5), (x + r * 0.5, y - r * 0.5)],
           fill=BLACK, width=LW, joint="curve")
    circ(d, x + r * 0.55, y - r * 0.12, r * 0.08)
    poly(d, [(x - r * 0.9, y + r * 0.15), (x - r * 0.35, y + r * 0.15), (x - r * 0.35, y + r * 0.27),
             (x - r * 0.9, y + r * 0.27)])


def tractor(d, x, y, r, rng):
    rect(d, x - r * 0.8, y - r * 0.9, x + r * 0.05, y - r * 0.8)
    rect(d, x - r * 0.7, y - r * 0.8, x - r * 0.05, y + r * 0.2)
    rect(d, x - r * 0.58, y - r * 0.7, x - r * 0.17, y - r * 0.3)
    rect(d, x + r * 0.05, y - r * 0.15, x + r * 0.9, y + r * 0.4)
    rect(d, x + r * 0.6, y - r * 0.55, x + r * 0.68, y - r * 0.15)
    for k in range(3):
        d.line([(x + r * 0.2 + k * r * 0.22, y - r * 0.05), (x + r * 0.2 + k * r * 0.22, y + r * 0.25)],
               fill=BLACK, width=LW - 3)
    circ(d, x - r * 0.45, y + r * 0.25, r * 0.55)
    circ(d, x - r * 0.45, y + r * 0.25, r * 0.25)
    circ(d, x - r * 0.45, y + r * 0.25, r * 0.08)
    circ(d, x + r * 0.65, y + r * 0.5, r * 0.3)
    circ(d, x + r * 0.65, y + r * 0.5, r * 0.12)


def rickshaw(d, x, y, r, rng):
    rect(d, x - r * 0.95, y - r * 0.7, x + r * 0.3, y - r * 0.6)
    rect(d, x - r * 0.85, y - r * 0.6, x + r * 0.2, y + r * 0.3)
    rect(d, x - r * 0.7, y - r * 0.45, x - r * 0.1, y - r * 0.05)
    poly(d, [(x + r * 0.2, y - r * 0.6), (x + r * 0.45, y - r * 0.1), (x + r * 0.2, y - r * 0.1)])
    poly(d, [(x + r * 0.2, y - r * 0.1), (x + r * 0.5, y - r * 0.1), (x + r * 0.7, y + r * 0.3),
             (x + r * 0.2, y + r * 0.3)])
    circ(d, x + r * 0.6, y + r * 0.08, r * 0.06)
    for wx, rr in ((x - r * 0.55, 0.24), (x + r * 0.5, 0.2)):
        circ(d, wx, y + r * 0.35, r * rr)
        circ(d, wx, y + r * 0.35, r * 0.08)


def submarine(d, x, y, r, rng):
    poly(d, [(x - r * 1.1, y - r * 0.2), (x - r * 0.95, y), (x - r * 1.1, y + r * 0.2)])
    d.line([(x, y - r * 0.55), (x, y - r * 0.8), (x + r * 0.22, y - r * 0.8)], fill=BLACK, width=LW,
           joint="curve")
    rect(d, x - r * 0.25, y - r * 0.55, x + r * 0.25, y - r * 0.2)
    ell(d, x - r, y - r * 0.32, x + r, y + r * 0.32)
    for k in (-0.45, 0, 0.45):
        circ(d, x + k * r, y, r * 0.1)
    for bx, by, br in ((1.25, -0.3, 0.07), (1.4, -0.5, 0.05), (1.3, -0.75, 0.06)):
        bubble(d, x + bx * r, y + by * r, br * r, rng)


def hotballoon(d, x, y, r, rng):
    ell(d, x - r * 0.7, y - r, x + r * 0.7, y + r * 0.3)
    d.ellipse([(x - r * 0.35) * 1, y - r, (x + r * 0.35), y + r * 0.3], outline=BLACK, width=LW - 3)
    for sx in (-1, 1):
        d.line([(x + sx * r * 0.45, y + r * 0.2), (x + sx * r * 0.2, y + r * 0.55)], fill=BLACK, width=LW - 2)
    rect(d, x - r * 0.25, y + r * 0.55, x + r * 0.25, y + r * 0.85)
    d.line([(x - r * 0.25, y + r * 0.68), (x + r * 0.25, y + r * 0.68)], fill=BLACK, width=LW - 4)


# (function, size, English, Hindi)
VEHICLES_NAMED = [
    (car, 150, "Car", "कार"), (bus, 190, "Bus", "बस"), (truck, 190, "Truck", "ट्रक"),
    (train, 160, "Train", "रेलगाड़ी"), (airplane, 200, "Aeroplane", "हवाई जहाज़"),
    (helicopter, 170, "Helicopter", "हेलीकॉप्टर"), (bicycle, 190, "Bicycle", "साइकिल"),
    (motorcycle, 190, "Motorcycle", "मोटरसाइकिल"), (tractor, 160, "Tractor", "ट्रैक्टर"),
    (rickshaw, 190, "Auto Rickshaw", "ऑटो रिक्शा"), (boat, 140, "Boat", "नाव"),
    (submarine, 185, "Submarine", "पनडुब्बी"), (rocket, 110, "Rocket", "रॉकेट"),
    (firetruck, 190, "Fire Truck", "दमकल"), (ambulance, 190, "Ambulance", "एम्बुलेंस"),
    (hotballoon, 170, "Hot Air Balloon", "गर्म हवा का गुब्बारा"),
]


def vehicles(d, rng):
    """Ek bada vehicle + uske niche naam (English aur Hindi).
    Sheet number badhne par vehicle ek ke baad ek badalta hai, isliye pas-pas ki sheets kabhi same nahi."""
    k = getattr(rng, "sheet_n", 0) // 10
    func, sz, en, hi = VEHICLES_NAMED[k % len(VEHICLES_NAMED)]
    func(d, W // 2, 740, int(sz * 2.0 * rng.uniform(0.94, 1.04)), rng)
    d.text((W // 2, 1160), en, BLACK, 104)
    if HAS_HINDI:
        d.text((W // 2, 1285), hi, BLACK, 112, font=get_hindi_font)
    placed = [(W // 2, 740, 420)] + [(W // 2 + dx, yy, 120) for dx in range(-480, 481, 120) for yy in (1160, 1285)]
    items = [(cloud, rng.randint(80, 105), 125) for _ in range(2)] + [(sun, 80, 130)]
    items += [(star, rng.randint(36, 52), 60) for _ in range(rng.randint(3, 5))]
    items += [(rng.choice([butterfly, heart, balloon]), 60, 80) for _ in range(rng.randint(1, 3))]
    placed = scatter(d, rng, items, 190, 1600, placed)
    sprinkle(d, rng, placed, 190, 1600, rng.randint(6, 10))


def treats(d, rng):
    items = [(apple, rng.randint(90, 120), 130) for _ in range(3)]
    items += [(icecream, rng.randint(90, 115), 150) for _ in range(3)]
    items += [(cupcake, rng.randint(90, 115), 140) for _ in range(3)]
    items += [(heart, rng.randint(60, 90), 85) for _ in range(3)]
    items += [(butterfly, 55, 75)] * 1 + [(star, 45, 60)] * 3
    placed = scatter(d, rng, items, 200, 1560)
    sprinkle(d, rng, placed, 200, 1580, 8)


# ---- keede-makode (Bugs theme ke liye)
def _eyes(d, x, y, r, gap=0.3, er=0.08):
    for sx in (-1, 1):
        dot(d, x + sx * r * gap, y, max(3, r * er))


def _smile(d, x, y, r, w=0.4):
    d.arc([x - r * w, y - r * w * 0.6, x + r * w, y + r * w], 20, 160, fill=BLACK, width=LW - 3)


def bee(d, x, y, r, rng):
    y += r * 0.2
    poly(d, rot_ellipse(x - r * 0.4, y - r * 0.75, r * 0.24, r * 0.45, 0.35))
    poly(d, rot_ellipse(x + r * 0.05, y - r * 0.77, r * 0.24, r * 0.45, -0.1))
    poly(d, [(x - r, y - r * 0.12), (x - r * 1.3, y), (x - r, y + r * 0.12)])
    xc, a, b = x - r * 0.225, r * 0.775, r * 0.5
    ell(d, x - r, y - b, x + r * 0.55, y + b)
    for xs in (x - r * 0.6, x - r * 0.25, x + r * 0.1):
        h = b * math.sqrt(1 - ((xs - xc) / a) ** 2)
        d.line([(xs, y - h), (xs, y + h)], fill=BLACK, width=LW - 2)
    d.line([(x + r * 0.6, y - r * 0.3), (x + r * 0.5, y - r * 0.85)], fill=BLACK, width=LW - 2)
    d.line([(x + r * 0.8, y - r * 0.3), (x + r * 1.0, y - r * 0.85)], fill=BLACK, width=LW - 2)
    dot(d, x + r * 0.5, y - r * 0.85, max(4, r * 0.06))
    dot(d, x + r * 1.0, y - r * 0.85, max(4, r * 0.06))
    circ(d, x + r * 0.7, y - r * 0.02, r * 0.36)
    _eyes(d, x + r * 0.7, y - r * 0.1, r * 0.4, 0.4, 0.09)
    _smile(d, x + r * 0.7, y + r * 0.05, r * 0.4, 0.45)


def ant(d, x, y, r, rng):
    for k, lx in enumerate((x - r * 0.2, x - r * 0.0, x + r * 0.2)):
        d.line([(lx, y + r * 0.15), (lx + (k - 1) * r * 0.2 + r * 0.1, y + r * 0.5),
                (lx + (k - 1) * r * 0.45, y + r * 0.85)], fill=BLACK, width=LW, joint="curve")
    ell(d, x - r, y - r * 0.38, x - r * 0.25, y + r * 0.38)
    ell(d, x - r * 0.3, y - r * 0.22, x + r * 0.2, y + r * 0.22)
    circ(d, x + r * 0.55, y - r * 0.05, r * 0.36)
    d.line([(x + r * 0.7, y - r * 0.38), (x + r * 0.95, y - r * 0.85), (x + r * 1.15, y - r * 0.8)],
           fill=BLACK, width=LW - 2, joint="curve")
    d.line([(x + r * 0.5, y - r * 0.4), (x + r * 0.55, y - r * 0.9), (x + r * 0.75, y - r * 0.95)],
           fill=BLACK, width=LW - 2, joint="curve")
    _eyes(d, x + r * 0.55, y - r * 0.12, r * 0.4, 0.4, 0.09)
    _smile(d, x + r * 0.55, y - r * 0.0, r * 0.4, 0.45)


def spider(d, x, y, r, rng):
    d.line([(x, y - r * 1.15), (x, y - r * 0.6)], fill=BLACK, width=LW - 3)
    for i in range(4):
        for sx in (-1, 1):
            d.line([(x + sx * r * 0.3, y - r * 0.1 + i * r * 0.12),
                    (x + sx * r * (0.95 + (0.1 if i in (1, 2) else 0)), y - r * 0.6 + i * r * 0.28),
                    (x + sx * r * 1.25, y + r * 0.1 + i * r * 0.42)],
                   fill=BLACK, width=LW, joint="curve")
    circ(d, x, y + r * 0.2, r * 0.55)
    circ(d, x, y - r * 0.4, r * 0.34)
    _eyes(d, x, y - r * 0.45, r * 0.5, 0.45, 0.1)
    _smile(d, x, y - r * 0.38, r * 0.4, 0.4)
    for sx in (-1, 1):
        circ(d, x + sx * r * 0.25, y + r * 0.1, r * 0.1)


def snail(d, x, y, r, rng):
    y += r * 0.1
    ell(d, x - r, y + r * 0.35, x + r * 0.75, y + r * 0.7)
    ell(d, x + r * 0.4, y - r * 0.05, x + r, y + r * 0.7)
    for sx, tx in ((0.62, 0.55), (0.85, 0.95)):
        d.line([(x + r * sx, y - r * 0.0), (x + r * tx, y - r * 0.5)], fill=BLACK, width=LW - 1)
        circ(d, x + r * tx, y - r * 0.5, r * 0.07)
    dot(d, x + r * 0.78, y + r * 0.22, max(3, r * 0.045))
    d.arc([x + r * 0.62, y + r * 0.2, x + r * 0.92, y + r * 0.5], 20, 160, fill=BLACK, width=LW - 3)
    circ(d, x - r * 0.2, y - r * 0.05, r * 0.68)
    d.ellipse([x - r * 0.2 - r * 0.42, y - r * 0.05 - r * 0.42, x - r * 0.2 + r * 0.42, y - r * 0.05 + r * 0.42],
              outline=BLACK, width=LW - 2)
    d.ellipse([x - r * 0.2 - r * 0.2, y - r * 0.05 - r * 0.2, x - r * 0.2 + r * 0.2, y - r * 0.05 + r * 0.2],
              outline=BLACK, width=LW - 2)


def caterpillar(d, x, y, r, rng):
    segs = []
    for i in range(5):
        cx = x - r * 0.95 + i * r * 0.42
        cy = y + math.sin(i * 1.3) * r * 0.14
        segs.append((cx, cy))
        d.line([(cx, cy + r * 0.3), (cx - r * 0.03, cy + r * 0.55)], fill=BLACK, width=LW)
    for cx, cy in segs:
        circ(d, cx, cy, r * 0.34)
        d.arc([cx - r * 0.12, cy - r * 0.1, cx + r * 0.12, cy + r * 0.14], 20, 160, fill=BLACK, width=LW - 4)
    hx, hy = x + r * 0.95, y - r * 0.12
    circ(d, hx, hy, r * 0.45)
    d.line([(hx - r * 0.15, hy - r * 0.4), (hx - r * 0.3, hy - r * 0.85)], fill=BLACK, width=LW - 2)
    d.line([(hx + r * 0.15, hy - r * 0.4), (hx + r * 0.3, hy - r * 0.85)], fill=BLACK, width=LW - 2)
    dot(d, hx - r * 0.3, hy - r * 0.85, max(4, r * 0.06))
    dot(d, hx + r * 0.3, hy - r * 0.85, max(4, r * 0.06))
    _eyes(d, hx, hy - r * 0.08, r * 0.5, 0.4, 0.1)
    _smile(d, hx, hy + r * 0.02, r * 0.5, 0.45)


def dragonfly(d, x, y, r, rng):
    for cx, cy, an in ((x + r * 0.15, y - r * 0.4, -0.25), (x - r * 0.25, y - r * 0.3, 0.2),
                       (x + r * 0.15, y + r * 0.4, 0.25), (x - r * 0.25, y + r * 0.3, -0.2)):
        poly(d, rot_ellipse(cx, cy, r * 0.5, r * 0.13, an))
    ell(d, x - r, y - r * 0.08, x + r * 0.6, y + r * 0.08)
    for k in range(6):
        sx = x - r * 0.85 + k * r * 0.22
        d.line([(sx, y - r * 0.08), (sx, y + r * 0.08)], fill=BLACK, width=LW - 4)
    ell(d, x + r * 0.35, y - r * 0.16, x + r * 0.62, y + r * 0.16)
    circ(d, x + r * 0.8, y, r * 0.2)
    dot(d, x + r * 0.85, y - r * 0.04, max(3, r * 0.045))
    d.arc([x + r * 0.78, y - r * 0.02, x + r * 0.95, y + r * 0.12], 20, 160, fill=BLACK, width=LW - 4)


def grasshopper(d, x, y, r, rng):
    y += r * 0.05
    d.line([(x - r * 0.88, y - r * 0.28), (x - r * 1.15, y + r * 0.62)], fill=BLACK, width=LW + 2)
    d.line([(x - r * 1.25, y + r * 0.62), (x - r * 1.0, y + r * 0.62)], fill=BLACK, width=LW + 2)
    for lx in (x + r * 0.3, x + r * 0.0):
        d.line([(lx, y + r * 0.2), (lx + r * 0.1, y + r * 0.4), (lx + r * 0.05, y + r * 0.62)],
               fill=BLACK, width=LW, joint="curve")
    poly(d, rot_ellipse(x - r * 0.25, y - r * 0.18, r * 0.65, r * 0.12, 0.12))
    ell(d, x - r * 0.8, y - r * 0.25, x + r * 0.5, y + r * 0.25)
    poly(d, rot_ellipse(x - r * 0.55, y - r * 0.0, r * 0.4, r * 0.14, 0.6))
    ell(d, x + r * 0.35, y - r * 0.35, x + r * 0.95, y + r * 0.2)
    d.line([(x + r * 0.7, y - r * 0.33), (x + r * 0.95, y - r * 0.85)], fill=BLACK, width=LW - 2)
    d.line([(x + r * 0.55, y - r * 0.33), (x + r * 0.55, y - r * 0.85)], fill=BLACK, width=LW - 2)
    dot(d, x + r * 0.72, y - r * 0.14, max(3, r * 0.06))
    d.arc([x + r * 0.7, y - r * 0.08, x + r * 0.9, y + r * 0.1], 20, 160, fill=BLACK, width=LW - 4)


def fly(d, x, y, r, rng):
    y += r * 0.1
    for sx in (-1, 1):
        poly(d, rot_ellipse(x + sx * r * 0.6, y + r * 0.2, r * 0.55, r * 0.22, (2.2 if sx < 0 else 0.94)))
        for k in range(3):
            d.line([(x + sx * r * 0.3, y - r * 0.05 + k * r * 0.2), (x + sx * r * 0.8, y + r * 0.0 + k * r * 0.3)],
                   fill=BLACK, width=LW - 2)
    ell(d, x - r * 0.4, y - r * 0.2, x + r * 0.4, y + r * 0.75)
    d.line([(x, y + r * 0.1), (x, y + r * 0.75)], fill=BLACK, width=LW - 3)
    circ(d, x, y - r * 0.4, r * 0.32)
    for sx in (-1, 1):
        circ(d, x + sx * r * 0.22, y - r * 0.5, r * 0.15)
        dot(d, x + sx * r * 0.22, y - r * 0.5, max(3, r * 0.05))
        d.line([(x + sx * r * 0.1, y - r * 0.7), (x + sx * r * 0.2, y - r * 0.95)], fill=BLACK, width=LW - 3)
    d.arc([x - r * 0.15, y - r * 0.42, x + r * 0.15, y - r * 0.2], 20, 160, fill=BLACK, width=LW - 4)


def beetle(d, x, y, r, rng):
    y += r * 0.1
    for k in range(3):
        for sx in (-1, 1):
            d.line([(x + sx * r * 0.5, y + k * r * 0.35), (x + sx * r * 0.9, y + k * r * 0.35 - r * 0.1 + (k - 1) * r * 0.1),
                    (x + sx * r * 1.1, y + k * r * 0.35 + r * 0.2)],
                   fill=BLACK, width=LW, joint="curve")
    poly(d, [(x - r * 0.15, y - r * 0.85), (x - r * 0.35, y - r * 1.25), (x - r * 0.05, y - r * 0.95)])
    poly(d, [(x + r * 0.15, y - r * 0.85), (x + r * 0.35, y - r * 1.25), (x + r * 0.05, y - r * 0.95)])
    ell(d, x - r * 0.6, y - r * 0.4, x + r * 0.6, y + r * 0.95)
    d.line([(x, y - r * 0.4), (x, y + r * 0.95)], fill=BLACK, width=LW - 2)
    for sx, sy, sr in ((-0.3, 0.0, 0.1), (0.3, 0.0, 0.1), (-0.3, 0.4, 0.1), (0.3, 0.4, 0.1), (-0.25, 0.75, 0.08), (0.25, 0.75, 0.08)):
        circ(d, x + sx * r, y + sy * r, sr * r)
    circ(d, x, y - r * 0.65, r * 0.3)
    _eyes(d, x, y - r * 0.7, r * 0.4, 0.4, 0.1)
    _smile(d, x, y - r * 0.62, r * 0.3, 0.45)


def firefly(d, x, y, r, rng):
    for k in range(10):
        a = 2 * math.pi * k / 10
        d.line([(x - r * 0.85 + math.cos(a) * r * 0.42, y + r * 0.1 + math.sin(a) * r * 0.42),
                (x - r * 0.85 + math.cos(a) * r * 0.65, y + r * 0.1 + math.sin(a) * r * 0.65)],
               fill=BLACK, width=LW - 2)
    poly(d, rot_ellipse(x - r * 0.1, y - r * 0.55, r * 0.5, r * 0.18, -0.4))
    for lx in (x - r * 0.25, x + r * 0.05):
        d.line([(lx, y + r * 0.2), (lx - r * 0.05, y + r * 0.55)], fill=BLACK, width=LW)
    ell(d, x - r * 0.75, y - r * 0.2, x + r * 0.35, y + r * 0.28)
    circ(d, x - r * 0.85, y + r * 0.1, r * 0.3)
    circ(d, x + r * 0.55, y - r * 0.05, r * 0.3)
    dot(d, x + r * 0.63, y - r * 0.12, max(3, r * 0.05))
    d.arc([x + r * 0.45, y - r * 0.08, x + r * 0.72, y + r * 0.15], 20, 160, fill=BLACK, width=LW - 4)
    d.line([(x + r * 0.55, y - r * 0.33), (x + r * 0.7, y - r * 0.7)], fill=BLACK, width=LW - 2)


def mosquito(d, x, y, r, rng):
    poly(d, rot_ellipse(x - r * 0.1, y - r * 0.45, r * 0.5, r * 0.13, -0.3))
    poly(d, rot_ellipse(x - r * 0.4, y - r * 0.38, r * 0.5, r * 0.13, 0.1))
    for sx, ex, ey in ((-0.2, -0.65, 1.0), (0.0, -0.05, 1.05), (0.15, 0.55, 0.95)):
        d.line([(x + sx * r, y + r * 0.1), (x + (sx + ex) / 2 * r - r * 0.15, y + r * 0.55), (x + ex * r, y + r * ey)],
               fill=BLACK, width=LW - 2, joint="curve")
    ell(d, x - r * 0.95, y - r * 0.12, x - r * 0.1, y + r * 0.16)
    circ(d, x + r * 0.0, y + r * 0.0, r * 0.24)
    circ(d, x + r * 0.42, y + r * 0.02, r * 0.2)
    dot(d, x + r * 0.5, y - r * 0.04, max(3, r * 0.04))
    d.line([(x + r * 0.58, y + r * 0.1), (x + r * 1.15, y + r * 0.4)], fill=BLACK, width=LW - 2)


def worm(d, x, y, r, rng):
    n = 40
    pts = [(x - r + 2 * r * t / n, y + math.sin(t / n * 2 * math.pi * 1.5) * r * 0.28) for t in range(n + 1)]
    w = r * 0.16
    d.line([(px, py - w) for px, py in pts], fill=BLACK, width=LW, joint="curve")
    d.line([(px, py + w) for px, py in pts], fill=BLACK, width=LW, joint="curve")
    circ(d, pts[0][0], pts[0][1], w)
    for i in range(3, n - 3, 4):
        d.line([(pts[i][0], pts[i][1] - w), (pts[i][0], pts[i][1] + w)], fill=BLACK, width=LW - 4)
    hx, hy = pts[-1]
    circ(d, hx, hy, r * 0.24)
    _eyes(d, hx, hy - r * 0.05, r * 0.3, 0.4, 0.1)
    _smile(d, hx, hy + r * 0.02, r * 0.3, 0.45)


def scorpion(d, x, y, r, rng):
    y += r * 0.3
    for k in range(4):
        for sx in (-1,):
            lx = x - r * 0.35 + k * r * 0.2
            d.line([(lx, y + r * 0.3), (lx - r * 0.15, y + r * 0.6), (lx - r * 0.1, y + r * 0.8)],
                   fill=BLACK, width=LW, joint="curve")
    tail = [(-0.65, 0.12, 0.17), (-0.85, -0.2, 0.16), (-0.85, -0.55, 0.15), (-0.65, -0.85, 0.14), (-0.35, -0.95, 0.13)]
    for tx, ty, tr in tail:
        circ(d, x + tx * r, y + ty * r, tr * r)
    poly(d, [(x - r * 0.2, y - r * 1.12), (x + r * 0.0, y - r * 0.85), (x - r * 0.18, y - r * 0.9)])
    d.line([(x + r * 0.3, y - r * 0.05), (x + r * 0.75, y - r * 0.25)], fill=BLACK, width=LW + 2)
    d.line([(x + r * 0.3, y + r * 0.2), (x + r * 0.75, y + r * 0.4)], fill=BLACK, width=LW + 2)
    for cy in (-0.4, 0.55):
        cx = x + r * 0.95
        poly(d, rot_ellipse(cx, y + r * cy, r * 0.3, r * 0.2, 0.0))
        poly(d, [(cx + r * 0.2, y + r * cy - r * 0.02), (cx + r * 0.5, y + r * cy), (cx + r * 0.2, y + r * cy + r * 0.12)])
    ell(d, x - r * 0.6, y - r * 0.15, x + r * 0.4, y + r * 0.4)
    _eyes(d, x + r * 0.05, y + r * 0.05, r * 0.5, 0.3, 0.09)
    _smile(d, x + r * 0.05, y + r * 0.15, r * 0.4, 0.4)


# (function, size, English, Hindi)
BUGS_NAMED = [
    (ladybug, 130, "Ladybug", "लेडीबग"), (butterfly, 150, "Butterfly", "तितली"), (bee, 185, "Bee", "मधुमक्खी"),
    (ant, 175, "Ant", "चींटी"), (spider, 150, "Spider", "मकड़ी"), (snail, 180, "Snail", "घोंघा"),
    (caterpillar, 180, "Caterpillar", "इल्ली"), (dragonfly, 210, "Dragonfly", "ड्रैगनफ्लाई"),
    (grasshopper, 180, "Grasshopper", "टिड्डा"), (fly, 160, "Fly", "मक्खी"),
    (beetle, 150, "Beetle", "भृंग"), (firefly, 190, "Firefly", "जुगनू"),
    (mosquito, 190, "Mosquito", "मच्छर"), (worm, 190, "Earthworm", "केंचुआ"),
    (scorpion, 170, "Scorpion", "बिच्छू"),
]


def bugs(d, rng):
    """Ek bada keeda + uske niche naam (English aur Hindi). Pas-pas ki sheets me keede alag-alag aate hain."""
    k = getattr(rng, "sheet_n", 0) // 10
    func, sz, en, hi = BUGS_NAMED[k % len(BUGS_NAMED)]
    func(d, W // 2, 740, int(sz * 2.0 * rng.uniform(0.94, 1.04)), rng)
    d.text((W // 2, 1160), en, BLACK, 104)
    if HAS_HINDI:
        d.text((W // 2, 1285), hi, BLACK, 112, font=get_hindi_font)
    placed = [(W // 2, 740, 420)] + [(W // 2 + dx, yy, 120) for dx in range(-480, 481, 120) for yy in (1160, 1285)]
    items = [(cloud, rng.randint(80, 105), 125), (sun, 80, 130)]
    items += [(flower, rng.randint(38, 50), 100) for _ in range(rng.randint(2, 3))]
    items += [(mushroom, rng.randint(70, 85), 105) for _ in range(rng.randint(0, 2))]
    items += [(star, rng.randint(36, 50), 60) for _ in range(rng.randint(2, 4))]
    placed = scatter(d, rng, items, 190, 1600, placed)
    sprinkle(d, rng, placed, 190, 1600, rng.randint(5, 9))


def rainbow_world(d, rng):
    ry = rng.randint(520, 600)
    rainbow(d, W // 2, ry + 120, 300, rng)
    placed = [(W // 2, ry - 20, 320)]
    items = [(kite, rng.randint(85, 105), 150) for _ in range(2)]
    items += [(balloon, rng.randint(80, 100), 135) for _ in range(3)]
    items += [(cloud, rng.randint(85, 105), 130) for _ in range(2)]
    items += [(sun, 85, 140)]
    items += [(rng.choice([rabbit, duck, turtle, cat]), 95, 160) for _ in range(2)]
    items += [(butterfly, 60, 80), (flower, 40, 100), (flower, 40, 100)]
    placed = scatter(d, rng, items, 200, 1580, placed)
    sprinkle(d, rng, placed, 200, 1580, 8)


POOL = [(sun, 95, 150), (cloud, 95, 125), (butterfly, 60, 80), (star, 50, 62), (fish, 90, 135),
        (balloon, 90, 135), (rocket, 115, 165), (car, 110, 130), (boat, 100, 130), (apple, 90, 105),
        (icecream, 90, 125), (heart, 70, 80), (moon, 85, 95), (flower, 45, 100), (cat, 130, 150),
        (owl, 120, 150), (house_c, 200, 170), (tree_c, 180, 160), (ladybug, 95, 135),
        (mushroom, 90, 125), (cupcake, 95, 125), (turtle, 95, 135), (duck, 90, 135),
        (rabbit, 70, 130), (kite, 90, 140), (rainbow_c, 170, 185)]


def surprise(d, rng):
    chosen = [rng.choice(POOL) for _ in range(rng.randint(9, 12))]
    chosen.sort(key=lambda t: -t[2])
    items = []
    for f, s, pr in chosen:
        k = rng.uniform(0.85, 1.2)
        items.append((f, int(s * k), int(pr * k)))
    placed = scatter(d, rng, items, 200, 1580)
    sprinkle(d, rng, placed, 200, 1580, 8)


def mandala(d, rng):
    cx, cy = W // 2, H // 2 + 20
    rings = rng.randint(5, 7)
    stp = rng.choice([66, 70, 74])
    for k in range(rings):
        dist = 480 - k * stp
        kind = rng.choice(["petal", "petal", "star", "circle", "tri", "dots"])
        n = rng.choice([10, 12, 16, 20]) if dist > 220 else rng.choice([6, 8, 10, 12])
        off = rng.random()
        la = min(70, stp)
        lb = max(12, min(40, math.pi * dist / n * 0.45))
        for i in range(n):
            a = 2 * math.pi * i / n + off
            px, py = cx + math.cos(a) * dist, cy + math.sin(a) * dist
            if kind == "petal":
                poly(d, rot_ellipse(px, py, la, lb, a))
            elif kind == "star":
                star(d, px, py, min(48, lb * 1.4 + 8), rng)
            elif kind == "circle":
                circ(d, px, py, min(42, lb + 8))
            elif kind == "tri":
                w = min(38, lb + 10)
                tip = (cx + math.cos(a) * (dist + 52), cy + math.sin(a) * (dist + 52))
                bx, by = cx + math.cos(a) * (dist - 12), cy + math.sin(a) * (dist - 12)
                nx, ny = -math.sin(a) * w, math.cos(a) * w
                poly(d, [tip, (bx + nx, by + ny), (bx - nx, by - ny)])
            else:
                dot(d, px, py, 11)
        d.ellipse([cx - dist + 25, cy - dist + 25, cx + dist - 25, cy + dist - 25],
                  fill=WHITE, outline=BLACK, width=LW - 2)
    circ(d, cx, cy, 55)
    circ(d, cx, cy, 28)
    dot(d, cx, cy, 8)


THEMES = {
    "Bagicha (Garden)": garden,
    "Samundar (Sea)": sea,
    "Aasman (Sky)": sky,
    "Janwar (Animals)": animals,
    "Gaadiyan (Vehicles)": vehicles,
    "Mazedaar (Treats)": treats,
    "Keede-Makode (Bugs)": bugs,
    "Rangeen Duniya (Rainbow)": rainbow_world,
    "Surprise (Sab kuch)": surprise,
    "Mandala": mandala,
}
TITLES = {
    "Bagicha (Garden)": "Mera Pyara Bagicha",
    "Samundar (Sea)": "Samundar ki Sair",
    "Aasman (Sky)": "Aasman me Udaan",
    "Janwar (Animals)": "Pyare Janwar",
    "Gaadiyan (Vehicles)": "Chhuk-Chhuk Gaadiyan",
    "Mazedaar (Treats)": "Yummy Treats!",
    "Keede-Makode (Bugs)": "Chhote Dost Keede",
    "Rangeen Duniya (Rainbow)": "Rangeen Duniya",
    "Surprise (Sab kuch)": "Surprise Sheet!",
    "Mandala": "Mandala Magic",
}
THEME_NAMES = list(THEMES)


def theme_of(n):
    """Sheet number se theme tay hota hai (1,2,3... alag-alag themes)."""
    return THEME_NAMES[(n - 1) % len(THEME_NAMES)]


# ----------------------------------------------------------------- page / book
def frame(cv, title, label):
    cv.rectangle([0, 0, W, 180], fill=WHITE)
    cv.rectangle([0, H - 150, W, H], fill=WHITE)
    cv.rectangle([0, 0, 34, H], fill=WHITE)       # frame ke bahar kuch na dikhe
    cv.rectangle([W - 34, 0, W, H], fill=WHITE)
    cv.rounded_rectangle([28, 28, W - 28, H - 28], 50, outline=BLACK, width=9)
    cv.rounded_rectangle([48, 48, W - 48, H - 48], 36, outline=BLACK, width=3)
    cv.rounded_rectangle([150, 68, W - 150, 166], 46, fill=WHITE, outline=BLACK, width=7)
    cv.text((W // 2, 117), title, BLACK, 62)
    for sx in (95, W - 95):
        star(cv, sx, 117, 34, None)
    cv.line([(90, H - 150), (W - 90, H - 150)], fill=BLACK, width=3)
    cv.text((95, H - 85), "Naam: ______________", BLACK, 40, "lm")
    cv.text((W - 95, H - 85), label, BLACK, 32, "rm")


def make_page(n):
    """Sheet number n (1..TOTAL) ki sheet. Same n = hamesha same sheet."""
    theme = theme_of(n)
    rng = random.Random(n)
    rng.sheet_n = n
    cv = Canvas()
    THEMES[theme](cv, rng)
    frame(cv, TITLES[theme], f"Sheet No. {n:,}")
    return cv.img.resize((W, H), Image.LANCZOS).convert("L")


def to_png(img):
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def make_pdf(pngs):
    images = [Image.open(io.BytesIO(p)).convert("RGB") for p in pngs]
    buf = io.BytesIO()
    images[0].save(buf, "PDF", resolution=150.0, save_all=True, append_images=images[1:])
    return buf.getvalue()


# ----------------------------------------------------------------- new objects (Varnamala ke liye)
def mango(d, x, y, r, rng):
    d.line([(x - r * 0.78, y - r * 0.5), (x - r * 0.9, y - r * 0.82)], fill=BLACK, width=LW)
    poly(d, rot_ellipse(x - r * 0.6, y - r * 0.9, r * 0.42, r * 0.16, -0.35))
    poly(d, rot_ellipse(x, y, r, r * 0.72, 0.45))
    face(d, x, y, r * 0.7)


def pomegranate(d, x, y, r, rng):  # anar
    poly(d, [(x - r * 0.3, y - r * 0.8), (x - r * 0.38, y - r * 1.3), (x - r * 0.14, y - r * 1.05),
             (x, y - r * 1.38), (x + r * 0.14, y - r * 1.05), (x + r * 0.38, y - r * 1.3),
             (x + r * 0.3, y - r * 0.8)])
    circ(d, x, y, r)
    face(d, x, y + r * 0.1, r * 0.75)


def glasses(d, x, y, r, rng):  # ainak
    d.line([(x - r * 1.0, y - r * 0.1), (x - r * 1.45, y - r * 0.4)], fill=BLACK, width=LW)
    d.line([(x + r * 1.0, y - r * 0.1), (x + r * 1.45, y - r * 0.4)], fill=BLACK, width=LW)
    circ(d, x - r * 0.55, y, r * 0.45)
    circ(d, x + r * 0.55, y, r * 0.45)
    d.arc([x - r * 0.15, y - r * 0.3, x + r * 0.15, y + r * 0.05], 180, 360, fill=BLACK, width=LW)
    for sx in (-1, 1):
        d.arc([x + sx * r * 0.55 - r * 0.28, y - r * 0.28, x + sx * r * 0.55 + r * 0.05, y + r * 0.05],
              190, 270, fill=BLACK, width=LW - 3)


def grapes(d, x, y, r, rng):  # angoor
    d.line([(x, y - r * 0.7), (x + r * 0.1, y - r * 1.1)], fill=BLACK, width=LW)
    poly(d, rot_ellipse(x + r * 0.5, y - r * 0.95, r * 0.42, r * 0.17, -0.4))
    for row, cnt in enumerate((3, 2, 1)):
        yy = y - r * 0.4 + row * r * 0.5
        for k in range(cnt):
            circ(d, x + (k - (cnt - 1) / 2) * r * 0.56, yy, r * 0.29)


def tomato(d, x, y, r, rng):
    ell(d, x - r, y - r * 0.8, x + r, y + r * 0.85)
    poly(d, rot_ellipse(x - r * 0.28, y - r * 0.8, r * 0.3, r * 0.1, 0.35))
    poly(d, rot_ellipse(x + r * 0.28, y - r * 0.8, r * 0.3, r * 0.1, -0.35))
    poly(d, rot_ellipse(x, y - r * 0.88, r * 0.1, r * 0.22, 0))
    face(d, x, y + r * 0.05, r * 0.8)


def umbrella(d, x, y, r, rng):  # chhatri
    d.line([(x, y), (x, y + r * 1.0)], fill=BLACK, width=LW)
    d.arc([x - r * 0.35, y + r * 0.82, x, y + r * 1.18], 0, 180, fill=BLACK, width=LW)
    poly(d, dome(x, y, r, r * 0.9))
    for k in (-0.5, 0, 0.5):
        d.line([(x, y - r * 0.9), (x + k * r * 1.2, y)], fill=BLACK, width=LW - 3)


def hand(d, x, y, s, count, mirror=False):
    """Haath: count ungliyan (0-5) khadi. (x, y) = hatheli ka upar ka beech, s = size."""
    m = -1 if mirror else 1
    ext = [False] * 4                       # slot 3 = tarjani (angutha ke paas)
    for k in range(min(count, 4)):
        ext[3 - k] = True
    lens = [1.15, 1.5, 1.7, 1.45]
    fw = s * 0.42
    if count >= 5:                          # angutha (palm ke peeche se)
        poly(d, rot_ellipse(x + m * s * 1.1, y + s * 0.45, s * 0.62, s * 0.24, -m * 0.95))
    for i in range(4):
        fx = x + m * (-s + (i + 0.5) * s / 2)
        L = s * lens[i] if ext[i] else s * 0.3
        d.rounded_rectangle([fx - fw / 2, y - L, fx + fw / 2, y + s * 0.4], fw / 2,
                            fill=WHITE, outline=BLACK, width=LW)
    pts = [(x - s, y), (x - s, y + 1.15 * s), (x - 0.7 * s, y + 1.55 * s),
           (x + 0.7 * s, y + 1.55 * s), (x + s, y + 1.15 * s), (x + s, y)]
    d.polygon(pts, fill=WHITE)
    d.line(pts, fill=BLACK, width=LW, joint="curve")
    if count < 5:                           # mudha hua angutha
        poly(d, rot_ellipse(x + m * s * 0.45, y + s * 0.75, s * 0.5, s * 0.18, m * 0.25))


# ----------------------------------------------------------------- Hindi font
try:
    HAS_RAQM = features.check("raqm")
except Exception:
    HAS_RAQM = False


@lru_cache(maxsize=1)
def hindi_font_path():
    """Devanagari font dhundta hai: pehle ./fonts/ folder, phir system fonts."""
    here = os.path.dirname(os.path.abspath(__file__))
    found = sorted(glob.glob(os.path.join(here, "fonts", "*.[to]t[fc]")))
    roots = ["/usr/share/fonts", "/usr/local/share/fonts", os.path.expanduser("~/.fonts"),
             os.path.expanduser("~/.local/share/fonts"), "C:/Windows/Fonts",
             "/System/Library/Fonts", "/Library/Fonts"]
    names = ["*Devanagari*", "*Deva*", "Lohit-Devanagari*", "Mukta*", "Hind*", "Mangal*",
             "Nirmala*", "Kohinoor*", "FreeSans*", "FreeSerif*"]
    system = []
    for root in roots:
        for nm in names:
            for ext in ("ttf", "otf", "ttc"):
                system += glob.glob(os.path.join(root, "**", f"{nm}.{ext}"), recursive=True)

    def rank(p):
        b = os.path.basename(p).lower()
        return ("serif" in b, "mono" in b, "oblique" in b or "italic" in b, "bold" not in b, len(b))

    def usable(p):
        try:
            return bool(ImageFont.truetype(p, 40).getmask("अक").getbbox())
        except Exception:
            return False

    for p in found + sorted(set(system), key=rank):
        if usable(p):
            return p
    # kuch nahi mila -> internet se ek baar download karke ./fonts/ me rakh lo
    import urllib.request
    base = "https://github.com/google/fonts/raw/main/ofl/"
    for url in (base + "notosansdevanagari/NotoSansDevanagari%5Bwdth%2Cwght%5D.ttf",
                base + "mukta/Mukta-Bold.ttf"):
        try:
            os.makedirs(os.path.join(here, "fonts"), exist_ok=True)
            dest = os.path.join(here, "fonts", os.path.basename(url.replace("%5B", "[").replace("%5D", "]").replace("%2C", ",")))
            if not os.path.exists(dest):
                urllib.request.urlretrieve(url, dest)
            if usable(dest):
                return dest
        except Exception:
            continue
    return None


HAS_HINDI = hindi_font_path() is not None


@lru_cache(maxsize=16)
def get_hindi_font(size):
    p = hindi_font_path()
    if not p:
        return get_font(size)
    engine = ImageFont.Layout.RAQM if HAS_RAQM else ImageFont.Layout.BASIC
    f = ImageFont.truetype(p, int(size), layout_engine=engine)
    if "bold" not in os.path.basename(p).lower():
        try:                                 # variable font ho to Bold weight lagao
            f.set_variation_by_name("Bold")
        except Exception:
            pass
    return f


DEVA_DIGITS = str.maketrans("0123456789", "०१२३४५६७८९")

# ----------------------------------------------------------------- Ginti 1-100
_ONES = ("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
         "fifteen sixteen seventeen eighteen nineteen").split()
_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]


def en_word(n):
    if n == 100:
        return "one hundred"
    if n < 20:
        return _ONES[n]
    t, o = divmod(n, 10)
    return _TENS[t] + ("-" + _ONES[o] if o else "")


HINDI_NUM = ("एक दो तीन चार पाँच छह सात आठ नौ दस "
             "ग्यारह बारह तेरह चौदह पंद्रह सोलह सत्रह अठारह उन्नीस बीस "
             "इक्कीस बाईस तेईस चौबीस पच्चीस छब्बीस सत्ताईस अट्ठाईस उनतीस तीस "
             "इकतीस बत्तीस तैंतीस चौंतीस पैंतीस छत्तीस सैंतीस अड़तीस उनतालीस चालीस "
             "इकतालीस बयालीस तैंतालीस चौवालीस पैंतालीस छियालीस सैंतालीस अड़तालीस उनचास पचास "
             "इक्यावन बावन तिरपन चौवन पचपन छप्पन सत्तावन अट्ठावन उनसठ साठ "
             "इकसठ बासठ तिरसठ चौंसठ पैंसठ छियासठ सड़सठ अड़सठ उनहत्तर सत्तर "
             "इकहत्तर बहत्तर तिहत्तर चौहत्तर पचहत्तर छिहत्तर सतहत्तर अठहत्तर उन्यासी अस्सी "
             "इक्यासी बयासी तिरासी चौरासी पचासी छियासी सत्तासी अट्ठासी नवासी नब्बे "
             "इक्यानवे बानवे तिरानवे चौरानवे पंचानवे छियानवे सत्तानवे अट्ठानवे निन्यानवे सौ").split()
assert len(HINDI_NUM) == 100

# (function, size) - 1..5 ke baad bade mascot
MASCOTS = [(cat, 170), (owl, 150), (rabbit, 105), (duck, 120), (turtle, 150),
           (fish, 150), (ladybug, 120), (mushroom, 130), (apple, 150), (sun, 110)]
# 20 tak ginne wali cheezein: (function, scale)
COUNTABLE = [(apple, 1.0), (star, 1.15), (heart, 1.0), (fish, 0.95), (butterfly, 1.0),
             (cupcake, 0.9), (ladybug, 0.85), (duck, 0.9), (sun, 0.7), (moon, 1.0),
             (icecream, 0.85), (mushroom, 0.9)]
GRAY = "#b4b4b4"


def tiny(d, kind, x, y, r):
    """21-100 ke liye halki-patli aakritiyan (gol / taara / dil)."""
    if kind == 0:
        d.ellipse([x - r, y - r, x + r, y + r], fill=WHITE, outline=BLACK, width=4)
        return
    pts = []
    if kind == 1:
        for i in range(10):
            rr = r * 1.15 if i % 2 == 0 else r * 0.5
            a = -math.pi / 2 + i * math.pi / 5
            pts.append((x + rr * math.cos(a), y + rr * math.sin(a)))
    else:
        for i in range(40):
            t = 2 * math.pi * i / 40
            pts.append((x + 16 * math.sin(t) ** 3 * r / 16 * 1.05,
                        y - (13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t)
                             - math.cos(4 * t)) * r / 16 * 1.05))
    d.polygon(pts, fill=WHITE)
    d.line(pts + [pts[0]], fill=BLACK, width=4, joint="curve")


def make_number_page(n):
    """Ginti sheet n (1..100): khokhla ank, fingers/haath, English + Hindi naam, ginne ke liye cheezein."""
    rng = random.Random(n)
    cv = Canvas()
    digits = len(str(n))
    if n == 100:
        cv.text((W // 2, 440), "100", WHITE, 400, stroke=8)
    else:
        cv.text((335, 440), str(n), WHITE, {1: 520, 2: 370}[digits], stroke=8)
        if n <= 5:
            hand(cv, 850, 455, 128, n)
        elif n <= 10:
            hand(cv, 725, 470, 88, 5)
            hand(cv, 1005, 470, 88, n - 5, mirror=True)
        else:
            func, sz = MASCOTS[n % len(MASCOTS)]
            func(cv, 860, 440, sz, rng)

    cv.text((W // 2, 730), en_word(n).capitalize(), BLACK, 100)
    if HAS_HINDI:
        cv.text((W // 2, 845), f"{HINDI_NUM[n - 1]}  ·  {str(n).translate(DEVA_DIGITS)}", BLACK, 96,
                font=get_hindi_font)

    # ginne wala hissa
    cols = min(5, n) if n <= 20 else 10
    rows = -(-n // cols)
    gx0, gx1, gy0, gy1 = 90, 1090, 930, 1590
    cw = (gx1 - gx0) / cols
    ch = min(cw, (gy1 - gy0) / rows)
    top = gy0 + ((gy1 - gy0) - rows * ch) / 2
    func, sc = COUNTABLE[(n - 1) % len(COUNTABLE)]
    for i in range(n):
        r_, c_ = divmod(i, cols)
        x = gx0 + (c_ + 0.5) * cw
        y = top + (r_ + 0.5) * ch
        if n <= 20:
            func(cv, x, y, min(90 if n <= 5 else 64, min(cw, ch) * 0.3) * sc, rng)
        else:
            tiny(cv, n % 3, x, y, min(30, ch * 0.34))
    if n > 20:
        for r_ in range(rows):
            cv.text((1138, top + (r_ + 0.5) * ch), str(min((r_ + 1) * 10, n)), GRAY, 30)

    frame(cv, "Ginti Seekho", f"Ginti {n} / 100")
    return cv.img.resize((W, H), Image.LANCZOS).convert("L")


# ----------------------------------------------------------------- Hindi Varnamala
def _flower_pic(d, x, y, r, rng):
    flower(d, x, y - 110, 70, rng)


def _kite_pic(d, x, y, r, rng):
    kite(d, x, y - 70, r, rng)


def _one_finger(d, x, y, r, rng):
    hand(d, x, y - 80, r, 1)


# picture key -> (function, size)
PICS = {
    "anar": (pomegranate, 150), "aam": (mango, 175), "ullu": (owl, 160), "ek": (_one_finger, 125),
    "ainak": (glasses, 140), "angoor": (grapes, 170), "kamal": (_flower_pic, 70),
    "khargosh": (rabbit, 105), "ghar": (house_c, 230), "chaand": (moon, 170),
    "chhatri": (umbrella, 150), "tamatar": (tomato, 150), "taara": (star, 170),
    "naav": (boat, 140), "patang": (_kite_pic, 90), "phal": (apple, 160), "battakh": (duck, 120),
    "machhli": (fish, 130), "van": (tree_c, 200), "suraj": (sun, 110),
}

# (akshar, roman, shabd, roman shabd, chitra)
LETTERS = [
    # swar
    ("अ", "A", "अनार", "Anar", "anar"), ("आ", "Aa", "आम", "Aam", "aam"),
    ("इ", "I", "इमली", "Imli", None), ("ई", "Ee", "ईख", "Eekh", None),
    ("उ", "U", "उल्लू", "Ullu", "ullu"), ("ऊ", "Oo", "ऊन", "Oon", None),
    ("ऋ", "Ri", "ऋषि", "Rishi", None), ("ए", "E", "एक", "Ek", "ek"),
    ("ऐ", "Ai", "ऐनक", "Ainak", "ainak"), ("ओ", "O", "ओखली", "Okhli", None),
    ("औ", "Au", "औरत", "Aurat", None), ("अं", "Am", "अंगूर", "Angoor", "angoor"),
    ("अः", "Ah", None, None, None),
    # vyanjan
    ("क", "Ka", "कमल", "Kamal", "kamal"), ("ख", "Kha", "खरगोश", "Khargosh", "khargosh"),
    ("ग", "Ga", "गमला", "Gamla", None), ("घ", "Gha", "घर", "Ghar", "ghar"),
    ("ङ", "Nga", None, None, None),
    ("च", "Cha", "चाँद", "Chaand", "chaand"), ("छ", "Chha", "छतरी", "Chhatri", "chhatri"),
    ("ज", "Ja", "जहाज़", "Jahaaz", None), ("झ", "Jha", "झंडा", "Jhanda", None),
    ("ञ", "Nya", None, None, None),
    ("ट", "Ta", "टमाटर", "Tamatar", "tamatar"), ("ठ", "Tha", "ठेला", "Thela", None),
    ("ड", "Da", "डमरू", "Damru", None), ("ढ", "Dha", "ढक्कन", "Dhakkan", None),
    ("ण", "Na", None, None, None),
    ("त", "Ta", "तारा", "Taara", "taara"), ("थ", "Tha", "थाली", "Thaali", None),
    ("द", "Da", "दवात", "Davaat", None), ("ध", "Dha", "धनुष", "Dhanush", None),
    ("न", "Na", "नाव", "Naav", "naav"),
    ("प", "Pa", "पतंग", "Patang", "patang"), ("फ", "Pha", "फल", "Phal", "phal"),
    ("ब", "Ba", "बत्तख", "Battakh", "battakh"), ("भ", "Bha", "भालू", "Bhaalu", None),
    ("म", "Ma", "मछली", "Machhli", "machhli"),
    ("य", "Ya", "यज्ञ", "Yagya", None), ("र", "Ra", "रथ", "Rath", None),
    ("ल", "La", "लट्टू", "Lattu", None), ("व", "Va", "वन", "Van", "van"),
    ("श", "Sha", "शेर", "Sher", None), ("ष", "Sha", "षट्कोण", "Shatkon", None),
    ("स", "Sa", "सूरज", "Sooraj", "suraj"), ("ह", "Ha", "हाथी", "Haathi", None),
    ("क्ष", "Ksha", "क्षत्रिय", "Kshatriya", None), ("त्र", "Tra", "त्रिशूल", "Trishul", None),
    ("ज्ञ", "Gya", "ज्ञानी", "Gyaani", None),
]


ANIMALS_NAMED = [(cat, 150, "Cat", "बिल्ली"), (owl, 140, "Owl", "उल्लू"), (rabbit, 95, "Rabbit", "खरगोश"),
                 (duck, 115, "Duck", "बत्तख"), (turtle, 130, "Turtle", "कछुआ"), (fish, 120, "Fish", "मछली"),
                 (butterfly, 130, "Butterfly", "तितली"), (ladybug, 115, "Ladybug", "लेडीबग")]


def animal_box(cv, i, rng):
    """Jin akshar/letter ka chitra nahi hai wahan ek pyara janwar + uska naam (English + Hindi)."""
    func, sz, en, hi = ANIMALS_NAMED[(i - 1) % len(ANIMALS_NAMED)]
    func(cv, 880, 390, sz, rng)
    cv.text((880, 595), en, BLACK, 52)
    if HAS_HINDI:
        cv.text((880, 660), hi, BLACK, 56, font=get_hindi_font)


def make_letter_page(i):
    """Varnamala sheet i (1..len(LETTERS)): khokhla akshar, chitra, shabd, likhne ki practice."""
    ch, rl, word, rw, pic = LETTERS[i - 1]
    rng = random.Random(i)
    cv = Canvas()
    size = 430 if len(ch) == 1 else 330
    cv.text((335, 450), ch, WHITE, size, font=get_hindi_font, stroke=8)

    if pic:
        func, sz = PICS[pic]
        func(cv, 880, 450, sz, rng)
    else:
        animal_box(cv, i, rng)

    if word:
        cv.text((W // 2, 760), f"{ch} से {word}", BLACK, 110, font=get_hindi_font)
        cv.text((W // 2, 865), f"{rl} se {rw}", BLACK, 64)
    else:
        cv.text((W // 2, 780), ch, BLACK, 120, font=get_hindi_font)
        cv.text((W // 2, 880), rl, BLACK, 64)

    cv.text((100, 950), "Likho (upar se trace karo):", BLACK, 42, "lm")
    for row, cy in enumerate((1045, 1190, 1335, 1480)):
        for yy in (cy - 65, cy + 65):
            cv.line([(95, yy), (W - 95, yy)], fill="#c8c8c8", width=3)
        for k in range(7):
            if k < (7, 3, 1, 0)[row]:
                cv.text((150 + k * 160, cy), ch, GRAY, 120, font=get_hindi_font)

    frame(cv, "Hindi Varnamala", f"Akshar {i} / {len(LETTERS)}")
    return cv.img.resize((W, H), Image.LANCZOS).convert("L")




# ----------------------------------------------------------------- A to Z
ALPHA = [
    ("A", "Apple", "apple"), ("B", "Butterfly", "butterfly"), ("C", "Cat", "cat"), ("D", "Duck", "duck"),
    ("E", "Elephant", None), ("F", "Fish", "fish"), ("G", "Grapes", "grapes"), ("H", "House", "house"),
    ("I", "Ice cream", "icecream"), ("J", "Juice", None), ("K", "Kite", "kite"), ("L", "Ladybug", "ladybug"),
    ("M", "Mango", "mango"), ("N", "Nest", None), ("O", "Owl", "owl"), ("P", "Pizza", None),
    ("Q", "Queen", None), ("R", "Rabbit", "rabbit"), ("S", "Sun", "sun"), ("T", "Tomato", "tomato"),
    ("U", "Umbrella", "umbrella"), ("V", "Van", None), ("W", "Watch", None), ("X", "Xylophone", None),
    ("Y", "Yo-yo", None), ("Z", "Zebra", None),
]
ABC_PICS = {
    "apple": (apple, 160), "butterfly": (butterfly, 150), "cat": (cat, 150), "duck": (duck, 120),
    "fish": (fish, 130), "grapes": (grapes, 170), "house": (house_c, 230), "icecream": (icecream, 130),
    "kite": (_kite_pic, 90), "ladybug": (ladybug, 140), "mango": (mango, 175), "owl": (owl, 160),
    "rabbit": (rabbit, 105), "sun": (sun, 110), "tomato": (tomato, 150), "umbrella": (umbrella, 150),
}


def make_abc_page(i):
    """A to Z sheet i (1..26): khokhla Aa, chitra, 'A for Apple', capital + small letters ki practice."""
    up, word, pic = ALPHA[i - 1]
    lo = up.lower()
    rng = random.Random(i)
    cv = Canvas()
    cv.text((335, 450), up + lo, WHITE, 240 if up in "MW" else 300, stroke=8)
    if pic:
        func, sz = ABC_PICS[pic]
        func(cv, 880, 450, sz, rng)
    else:
        animal_box(cv, i, rng)
    cv.text((W // 2, 790), f"{up} for {word}", BLACK, 110)
    cv.text((100, 950), "Likho (upar se trace karo):", BLACK, 42, "lm")
    for row, cy in enumerate((1045, 1190, 1335, 1480)):
        for yy in (cy - 65, cy + 65):
            cv.line([(95, yy), (W - 95, yy)], fill="#c8c8c8", width=3)
        for k in range(7):
            if k < (7, 3, 1, 0)[row]:
                cv.text((150 + k * 160, cy), up if row % 2 == 0 else lo, GRAY, 120)
    frame(cv, "A to Z", f"Letter {i} / 26")
    return cv.img.resize((W, H), Image.LANCZOS).convert("L")


# ----------------------------------------------------------------- Photo -> Drawing
PHOTO_BOX = (70, 200, W - 70, H - 160)   # frame ke andar photo ki jagah


def soft_outline(rgb, detail, level):
    """Halki, patli pencil-jaisi outline (drawing book / reference sheet jaisi). Andar khali, rang bharne layak."""
    a = np.asarray(rgb)
    for _ in range(2):
        a = cv2.bilateralFilter(a, 9, 40, 9)
    g = cv2.cvtColor(a, cv2.COLOR_RGB2GRAY)
    g = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(g)
    r = max(5, int(25 - detail * 2)) | 1                         # detail zyada -> chhoti cheezein bhi
    bl = cv2.GaussianBlur(255 - g, (0, 0), r / 3)
    sk = cv2.divide(g, 255 - bl, scale=256).astype(np.float32)   # color-dodge: sirf kinare bachte hain
    gam = (1.0 + (10 - level) * 0.12) * 2.4                      # level zyada -> lines gehri
    sk = 255 * np.power(np.clip(sk, 0, 255) / 255.0, gam)
    dark = cv2.GaussianBlur((g < 60).astype(np.float32), (0, 0), 3)
    sk = np.maximum(sk, 255 * 0.55 * dark)                       # kaale dhabbe halke kar do
    sk = cv2.fastNlMeansDenoising(np.clip(sk, 0, 255).astype(np.uint8), None, 10, 7, 21)
    sk = np.clip((sk.astype(np.float32) - 40) * 1.18, 0, 255)     # lines thodi gehri, safedi saaf
    return Image.fromarray(sk.astype(np.uint8))


def photo_sheet(raw, detail=5, thick=2, level=5, title="Meri Drawing", style=0):
    """Photo (bytes) ko drawing-book jaisi patli, saaf outline me badalta hai - andar khali, rang bharne ke liye.
    detail: kam = sirf badi lines, zyada = chhoti cheezein bhi. level: kitni lines (zyada = halki lines bhi).
    thick: 1 = bahut patli, 2 = patli, 3 = thodi moti."""
    im = Image.open(io.BytesIO(raw))
    im = ImageOps.exif_transpose(im)
    im.thumbnail((2400, 2400))
    im = im.convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    bg.alpha_composite(im)
    rgb = bg.convert("RGB")
    x0, y0, x1, y1 = PHOTO_BOX
    bw, bh = x1 - x0, y1 - y0
    rgb = ImageOps.contain(rgb, (bw, bh), Image.LANCZOS)

    if style == 0:                                              # halki pencil-jaisi outline
        lines = soft_outline(rgb, detail, level)
        page = Image.new("L", (W, H), 255)
        page.paste(lines, (x0 + (bw - lines.width) // 2, y0 + (bh - lines.height) // 2))
        cv_ = Canvas()
        frame(cv_, (title or "Meri Drawing")[:24], "Photo Drawing")
        fr = cv_.img.resize((W, H), Image.LANCZOS).convert("L")
        return ImageChops.darker(fr, page)

    a = np.asarray(rgb)
    for _ in range(3):
        a = cv2.bilateralFilter(a, 9, 45, 9)            # texture mitao, kinare bachao
    g = cv2.cvtColor(a, cv2.COLOR_RGB2GRAY)
    g = cv2.GaussianBlur(g, (0, 0), 2.0)
    hi = max(8.0, 38 - level * 2.8)                      # level zyada -> halke kinare bhi aayenge
    e = cv2.Canny(g, hi * 0.45, hi)                      # ek-pixel patli line
    e = cv2.dilate(e, np.ones((3, 3), np.uint8))         # tooti lines jodo

    # chhote tukde / daag hatao, sirf lambi lines rakho
    n, lab, stats, _ = cv2.connectedComponentsWithStats((e > 0).astype(np.uint8), connectivity=8)
    min_area = int((40 + (10 - detail) * 5) * 3)
    ok = stats[:, cv2.CC_STAT_AREA] >= min_area
    ok[0] = False
    e = ok[lab]

    out = np.where(e, 0, 255).astype(np.uint8)
    k = (1, 3, 5)[thick - 1]
    if k > 1:
        out = cv2.erode(out, np.ones((k, k), np.uint8))
    out = cv2.GaussianBlur(out, (0, 0), 0.8)
    lines = Image.fromarray(np.where(out < 170, 0, 255).astype(np.uint8))

    page = Image.new("L", (W, H), 255)
    page.paste(lines, (x0 + (bw - lines.width) // 2, y0 + (bh - lines.height) // 2))

    cv_ = Canvas()
    frame(cv_, (title or "Meri Drawing")[:24], "Photo Drawing")
    fr = cv_.img.resize((W, H), Image.LANCZOS).convert("L")
    return ImageChops.darker(fr, page)


# ===== UI =====================================================================
st.set_page_config(page_title="Drawing Book", page_icon="🎨", layout="wide")

SINGLE, GALLERY = "📄 Ek sheet", "🖼️ Gallery (6 sheets)"


@st.cache_data(show_spinner="Sheet ban rahi hai... ✏️", max_entries=120)
def sheet_png(n):
    return to_png(make_page(n))


def allowed_themes():
    return set(st.session_state.get("chosen") or THEME_NAMES)


def step_sheet(n, direction, allowed):
    for _ in range(len(THEME_NAMES)):
        n += direction
        if n > TOTAL:
            n = 1
        if n < 1:
            n = TOTAL
        if theme_of(n) in allowed:
            return n
    return n


def cb_random():
    n = random.SystemRandom().randint(1, TOTAL)
    al = allowed_themes()
    if theme_of(n) not in al:
        n = step_sheet(n, 1, al)
    st.session_state.sheet_no = n


def cb_move(direction):
    al = allowed_themes()
    n = st.session_state.sheet_no
    count = 6 if st.session_state.view == GALLERY else 1
    for _ in range(count):
        n = step_sheet(n, direction, al)
    st.session_state.sheet_no = n


def cb_open(n):
    st.session_state.sheet_no = n
    st.session_state.view = SINGLE




# ===== Bachon wala look ==========================================================
KID_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Baloo+2:wght@500;700;800&display=swap');
html, body, .stApp, .stApp * {font-family: 'Baloo 2', 'Comic Sans MS', sans-serif;}
.stApp {background: radial-gradient(circle at 10% 10%, #fff3c4 0, transparent 35%),
        radial-gradient(circle at 90% 15%, #ffd6e8 0, transparent 35%),
        radial-gradient(circle at 15% 90%, #cdeeff 0, transparent 35%),
        radial-gradient(circle at 90% 85%, #d6ffe2 0, transparent 35%), #fffaf0;}
[data-testid="stHeader"] {background: transparent;}
h1 {font-weight: 800 !important; font-size: 3.2rem !important; text-align: center; padding-bottom: .2rem;
    background: linear-gradient(90deg,#ff5e62,#ff9966,#f5b700,#2ec4a0,#3a86ff,#9b5de5);
    -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;}
[data-testid="stMarkdownContainer"] p {font-size: 1.15rem;}
[data-testid="stMain"] [data-testid="stMarkdownContainer"] > p:first-child {text-align: center;}
/* mode pills */
div[role="radiogroup"] {gap: .7rem; flex-wrap: wrap; justify-content: center;}
div[role="radiogroup"] > label {background: #fff; border: 4px solid #ffd166; border-radius: 999px;
    padding: .35rem 1.3rem; box-shadow: 0 6px 0 #f0b429; cursor: pointer; transition: transform .1s;}
div[role="radiogroup"] > label:hover {transform: translateY(-3px) rotate(-1deg);}
div[role="radiogroup"] > label > div:first-child {display: none;}
div[role="radiogroup"] > label p {font-size: 1.35rem !important; font-weight: 800; margin: 0;}
div[role="radiogroup"] > label:has(input:checked) {background: linear-gradient(135deg,#ff9966,#ff5e62);
    border-color: #fff; box-shadow: 0 6px 0 #c0392b;}
div[role="radiogroup"] > label:has(input:checked) p {color: #fff;}
/* buttons */
div.stButton > button, div.stDownloadButton > button {border-radius: 999px; border: 4px solid #fff;
    font-weight: 800; font-size: 1.2rem; padding: .55rem 1.5rem; color: #fff;
    background: linear-gradient(135deg,#7b5cff,#4fa3ff); box-shadow: 0 6px 0 rgba(60,40,140,.35);
    transition: transform .08s, box-shadow .08s;}
div.stButton > button:hover, div.stDownloadButton > button:hover {transform: translateY(-3px); color: #fff;
    border-color: #fff; box-shadow: 0 9px 0 rgba(60,40,140,.35);}
div.stButton > button:active, div.stDownloadButton > button:active {transform: translateY(4px);
    box-shadow: 0 2px 0 rgba(60,40,140,.35);}
div.stButton > button p, div.stDownloadButton > button p {font-size: 1.2rem; font-weight: 800;}
div.stButton > button[kind="primary"] {background: linear-gradient(135deg,#ff9966,#ff5e62);
    box-shadow: 0 6px 0 rgba(160,50,30,.4);}
div.stDownloadButton > button {background: linear-gradient(135deg,#2ec4a0,#3a86ff);
    box-shadow: 0 6px 0 rgba(20,100,100,.35);}
/* sheet picture */
[data-testid="stImage"] img {border-radius: 26px; border: 8px solid #fff;
    box-shadow: 0 14px 34px rgba(80,60,120,.25); background: #fff;}
[data-testid="stImageCaption"], [data-testid="stCaptionContainer"] {text-align: center; font-weight: 700;}
/* inputs, expander, sidebar, progress */
[data-baseweb="input"], [data-baseweb="select"] > div {border-radius: 18px !important; border: 3px solid #cdb4ff !important;
    background: #fff !important;}
[data-testid="stExpander"] {background: rgba(255,255,255,.85); border: 4px dashed #ffb703; border-radius: 22px;}
[data-testid="stExpander"] summary p {font-size: 1.25rem; font-weight: 800;}
[data-testid="stSidebar"] {background: linear-gradient(180deg,#e9f2ff,#f4e9ff);
    border-right: 4px dotted #b79cff;}
[data-testid="stProgress"] div[role="progressbar"] > div {background: linear-gradient(90deg,#ff5e62,#f5b700,#2ec4a0,#3a86ff);}
[data-testid="stAlert"] {border-radius: 20px;}
</style>
"""


def inject_css():
    st.markdown(KID_CSS, unsafe_allow_html=True)


# ===== Seekho UI (Ginti / Varnamala) ==========================================
MODE_DRAW, MODE_NUM, MODE_ABC, MODE_HINDI = ("🎨 Drawing sheets", "🔢 Ginti (1 se 100)",
                                              "🔠 A to Z", "🔤 Hindi Varnamala")
MODE_PHOTO = "📷 Photo → Outline"


@st.cache_data(show_spinner="Sheet ban rahi hai... ✏️", max_entries=120)
def learn_png(kind, i):
    return to_png({"num": make_number_page, "abc": make_abc_page, "hindi": make_letter_page}[kind](i))


def learn_ui(mode):
    is_num = mode == MODE_NUM
    is_abc = mode == MODE_ABC
    kind = "num" if is_num else "abc" if is_abc else "hindi"
    total = 100 if is_num else 26 if is_abc else len(LETTERS)
    key = {"num": "ginti_no", "abc": "abc_no", "hindi": "akshar_no"}[kind]
    if key not in st.session_state:
        st.session_state[key] = 1

    def step(delta):
        st.session_state[key] = (st.session_state[key] - 1 + delta) % total + 1

    if is_num:
        st.title("🔢 Ginti Seekho — 1 se 100")
        st.write("Har sheet par: khokhla ank (rang bharo), English + Hindi naam, ungliyan aur ginne ki cheezein. 🖍️")
    elif is_abc:
        st.title("🔠 A to Z — Alphabet")
        st.write("A for Apple, B for Butterfly... khokhla letter, chitra aur capital + small letters likhne ki practice. 🖍️")
    else:
        st.title("🔤 Hindi Varnamala — अ से ज्ञ")
        st.write("Swar aur vyanjan: akshar, shabd, chitra aur likhne ki practice. (अ से अनार, आ से आम...) 🖍️")
        if not HAS_HINDI:
            st.error("Hindi (Devanagari) font nahi mila aur download bhi nahi hua. App ke saath ek `fonts/` "
                     "folder banao aur usme `NotoSansDevanagari-Bold.ttf` rakh do.")
            return
        if not HAS_RAQM:
            st.warning("Is server par Pillow ka `raqm` nahi hai, isliye कुछ matra (जैसे इ, ि) galat jud sakte hain. "
                       "Ye server ki setting hai (libraqm/libfribidi); app me iska koi aur upay nahi.")
    if is_num and not HAS_HINDI:
        st.info("Hindi font nahi mila, isliye sirf English naam dikh rahe hain. "
                "`fonts/` folder me Devanagari font rakho to Hindi naam bhi aayenge.")

    def pick_random():
        st.session_state[key] = random.SystemRandom().randint(1, total)

    c1, c2, c4, c3 = st.columns([1, 1, 1.2, 1.6])
    c1.button("⬅️ Pichli", on_click=step, args=(-1,), key=f"prev_{key}")
    c2.button("Agli ➡️", on_click=step, args=(1,), key=f"next_{key}", type="primary")
    c4.button("🎲 Koi bhi!", on_click=pick_random, key=f"rnd_{key}")
    if is_num:
        c3.number_input("Number", min_value=1, max_value=total, step=1, key=key)
    elif is_abc:
        c3.selectbox("Letter chuno", list(range(1, 27)), key=key,
                     format_func=lambda i: f"{ALPHA[i - 1][0]}  ({ALPHA[i - 1][1]})")
    else:
        c3.selectbox("Akshar chuno", list(range(1, total + 1)), key=key,
                     format_func=lambda i: f"{LETTERS[i - 1][0]}  ({LETTERS[i - 1][1]})")

    i = int(st.session_state[key])
    st.progress(i / total, text=f"⭐ {i} / {total} — shabaash! Aise hi aage badho!")
    png = learn_png(kind, i)
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        st.image(png, caption=f"Sheet {i} / {total}")
        d1, d2 = st.columns(2)
        stem = {"num": "ginti", "abc": "a_to_z", "hindi": "varnamala"}[kind]
        d1.download_button("⬇️ PNG download", png, file_name=f"{stem}_{i}.png", mime="image/png", key=f"lp_{key}_{i}")
        d2.download_button("📄 PDF download", make_pdf([png]), file_name=f"{stem}_{i}.pdf",
                           mime="application/pdf", key=f"lf_{key}_{i}")

    with st.expander("🖨️ Print pack — kai sheets ek hi PDF me"):
        a, b = st.slider("Kaun si sheets?", 1, total, (1, min(10, total)), key=f"rng_{key}")
        if b - a + 1 > 30:
            b = a + 29
            st.caption("Ek PDF me max 30 sheets — baaki ke liye dobara pack banao.")
        if st.button("📦 Pack banao", key=f"mk_{key}"):
            with st.spinner("Pack ban raha hai..."):
                st.session_state[f"pack_{key}"] = (a, b, make_pdf([learn_png(kind, m) for m in range(a, b + 1)]))
            st.balloons()
        if f"pack_{key}" in st.session_state:
            pa, pb, pdf = st.session_state[f"pack_{key}"]
            st.download_button(f"📄 Sheets {pa}–{pb} ka PDF download karo", pdf,
                               file_name=f"{ {'num': 'ginti', 'abc': 'a_to_z', 'hindi': 'varnamala'}[kind] }_{pa}_{pb}.pdf",
                               mime="application/pdf", key=f"dlp_{key}")


@st.cache_data(show_spinner="Outline ban rahi hai... ✏️", max_entries=40)
def photo_png(raw, detail, thick, level, title, style):
    return to_png(photo_sheet(raw, detail, thick, level, title, style))


def photo_ui():
    st.title("📷 Photo se Outline Sheet")
    st.write("Apni photo upload karo — hum uski sirf outline bana denge, andar khali, "
             "taaki aap rang bhar sako. 🖍️")
    files = st.file_uploader("Photo chuno (ek ya kai)", type=["png", "jpg", "jpeg", "webp", "bmp"],
                             accept_multiple_files=True, key="photo_files")
    style_name = st.radio("Outline ka style", ["✏️ Halki pencil outline (drawing book jaisi)", "🖊️ Patli pen outline (saaf lines)"],
                          key="photo_style", horizontal=True)
    style = 0 if style_name.startswith("✏️") else 1
    title = st.text_input("Sheet ka title", "Meri Drawing", max_chars=24, key="photo_title")
    s1, s2, s3 = st.columns(3)
    detail = s1.slider("Detail (kam = simple, zyada = bahut chhoti cheezein)", 1, 10, 5, key="photo_detail")
    level = s2.slider("Kitni lines (kam = sirf mukhya, zyada = sab)", 1, 10, 5, key="photo_level")
    thick = s3.slider("Line ki motai (sirf pen style me)", 1, 3, 2, key="photo_thick")
    st.caption("Tip: saaf, roshan photo jisme ek hi cheez/chehra ho, sabse achhi outline banati hai. "
               "Lines uljhi hon to Detail ya 'Kitni lines' kam karo; lines kam hon to badhao.")
    if not files:
        st.info("⬆️ Upar photo upload karo. Ek saath kai photos bhi daal sakte ho.")
        return
    files = files[:20]
    pngs = []
    for k, f in enumerate(files):
        raw = f.getvalue()
        try:
            png = photo_png(raw, detail, thick, level, title, style)
        except Exception:
            st.error(f"'{f.name}' photo nahi khul payi. Dusri photo (JPG/PNG) try karo.")
            continue
        pngs.append(png)
        a, b = st.columns(2)
        a.image(raw, caption=f"Original: {f.name}")
        b.image(png, caption="Outline sheet")
        d1, d2 = b.columns(2)
        stem = f"photo_outline_{k + 1}"
        d1.download_button("⬇️ PNG", png, file_name=f"{stem}.png", mime="image/png", key=f"ph_png_{k}")
        d2.download_button("📄 PDF", make_pdf([png]), file_name=f"{stem}.pdf", mime="application/pdf",
                           key=f"ph_pdf_{k}")
    if len(pngs) > 1:
        st.download_button(f"📦 Sab {len(pngs)} sheets ek PDF me", make_pdf(pngs),
                           file_name="photo_outlines.pdf", mime="application/pdf", key="ph_all")


if "chosen" not in st.session_state:
    st.session_state.chosen = THEME_NAMES[:]
if "view" not in st.session_state:
    st.session_state.view = SINGLE
if "sheet_no" not in st.session_state:
    cb_random()

inject_css()
st.radio("Kya karna hai?", [MODE_DRAW, MODE_NUM, MODE_ABC, MODE_HINDI, MODE_PHOTO], key="mode",
         horizontal=True, label_visibility="collapsed")
if st.session_state.mode == MODE_PHOTO:
    photo_ui()
    st.stop()
if st.session_state.mode != MODE_DRAW:
    learn_ui(st.session_state.mode)
    st.stop()

st.title("🎨 Bacho ki Drawing Book 🌈")
st.write(f"**{TOTAL:,} alag-alag drawing sheets!** Random dabao ya number likho — "
         "download karo, print karo aur rang bharo. 🖍️")

with st.sidebar:
    st.header("Settings")
    st.radio("Kaise dekhna hai?", [SINGLE, GALLERY], key="view")
    st.multiselect("Kaunse themes?", THEME_NAMES, key="chosen")
    st.caption("Har sheet number ki sheet hamesha wahi rehti hai — pasand aayi sheet ka number "
               "yaad rakho, baad me wapas khol lo.")

b1, b2, b3, b4 = st.columns([1, 1.2, 1, 2])
b1.button("⬅️ Pichli", on_click=cb_move, args=(-1,))
b2.button("🎲 Random sheet", type="primary", on_click=cb_random)
b3.button("Agli ➡️", on_click=cb_move, args=(1,))
b4.number_input(f"Sheet number (1 se {TOTAL:,})", min_value=1, max_value=TOTAL, step=1, key="sheet_no")

n = int(st.session_state.sheet_no)

if st.session_state.view == SINGLE:
    png = sheet_png(n)
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        st.image(png, caption=f"Sheet No. {n:,} · {theme_of(n)}")
        c1, c2 = st.columns(2)
        c1.download_button("⬇️ PNG download", png, file_name=f"drawing_sheet_{n}.png",
                           mime="image/png", key=f"png_{n}")
        c2.download_button("📄 PDF download", make_pdf([png]), file_name=f"drawing_sheet_{n}.pdf",
                           mime="application/pdf", key=f"pdf_{n}")
else:
    al = allowed_themes()
    nums = [n]
    while len(nums) < 6:
        nums.append(step_sheet(nums[-1], 1, al))
    for row in (nums[:3], nums[3:]):
        cols = st.columns(3)
        for col, m in zip(cols, row):
            with col:
                png = sheet_png(m)
                st.image(png, caption=f"Sheet No. {m:,} · {theme_of(m)}")
                st.button("🔍 Ye sheet kholo", key=f"open_{m}", on_click=cb_open, args=(m,))
                st.download_button("⬇️ Download", png, file_name=f"drawing_sheet_{m}.png",
                                   mime="image/png", key=f"g_png_{m}")

with st.expander("🖨️ Print pack — kai sheets ek hi PDF me"):
    k = st.slider("Kitni sheets?", 1, 20, 6)
    mode = st.radio("Kaunsi sheets?", ["Isi sheet se aage ki", "Random sheets"], horizontal=True)
    if st.button("📦 Pack banao"):
        al = allowed_themes()
        if mode == "Random sheets":
            nums = []
            while len(nums) < k:
                m = random.SystemRandom().randint(1, TOTAL)
                if theme_of(m) in al and m not in nums:
                    nums.append(m)
        else:
            nums = [n]
            while len(nums) < k:
                nums.append(step_sheet(nums[-1], 1, al))
        with st.spinner("Pack ban raha hai..."):
            st.session_state.pack = (nums, make_pdf([sheet_png(m) for m in nums]))
    if "pack" in st.session_state:
        nums, pdf = st.session_state.pack
        st.write("Sheet numbers: " + ", ".join(f"{m:,}" for m in nums))
        st.download_button(f"📄 {len(nums)} sheets ka PDF download karo", pdf,
                           file_name="drawing_pack.pdf", mime="application/pdf", key="dl_pack")
