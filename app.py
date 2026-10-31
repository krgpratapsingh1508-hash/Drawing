"""Bacho ki Drawing Book - ek hi file me (app + drawing engine).

* 1,000,000,000 (1 arab) alag-alag sheets: har sheet number ki sheet hamesha wahi rehti hai.
* Smooth lines (2x render), pyare chehre, frame, 10 themes.
* Sirf Streamlit + Pillow.
"""
import io
import math
import random
from functools import lru_cache

import streamlit as st
from PIL import Image, ImageDraw, ImageFont

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

    def text(self, xy, text, fill, size, anchor="mm"):
        self.d.text((xy[0] * self.s, xy[1] * self.s), text, fill=fill,
                    font=get_font(size * self.s), anchor=anchor)

    def font_text(self, xy, text, fill, maker, size, anchor="mm", stroke=0, stroke_fill=None):
        """maker(pixel_size) -> font. stroke>0 + fill=WHITE => khokhla (outline) akshar."""
        kw = {}
        if stroke:
            kw = dict(stroke_width=int(stroke * self.s), stroke_fill=stroke_fill)
        self.d.text((xy[0] * self.s, xy[1] * self.s), text, fill=fill,
                    font=maker(size * self.s), anchor=anchor, **kw)


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
    layout = rng.choice(["big2", "grid"])
    if layout == "big2":
        picks = rng.sample(ANIMALS, 2)
        placed = []
        for (func, k), y in zip(picks, (640, 1265)):
            r = int(300 * k)
            func(d, W // 2, y, r, rng)
            placed.append((W // 2, y, int(r * 1.15) + 40))
        items = [(butterfly, 55, 75)] * 2 + [(star, 42, 55)] * 3 + [(flower, 38, 95)] * 2
        placed = scatter(d, rng, items, 190, 1600, placed)
        sprinkle(d, rng, placed, 190, 1600, 8)
    else:
        items = []
        for _ in range(6):
            func, k = rng.choice(ANIMALS)
            r = int(rng.randint(105, 125) * k)
            items.append((func, r, int(r * 1.7)))
        placed = scatter(d, rng, items, 200, 1580)
        placed = scatter(d, rng, [(star, 42, 55)] * 3 + [(flower, 36, 90)] * 2, 200, 1580, placed)
        sprinkle(d, rng, placed, 200, 1580, 8)


def vehicles(d, rng):
    items = [(car, rng.randint(110, 150), 190) for _ in range(3)]
    items += [(boat, rng.randint(100, 130), 170), (rocket, 120, 170)]
    items += [(cloud, rng.randint(80, 110), 130) for _ in range(2)]
    items += [(sun, 80, 130)] + [(star, rng.randint(35, 55), 65) for _ in range(3)]
    placed = scatter(d, rng, items, 200, 1580)
    sprinkle(d, rng, placed, 200, 1580, 8)


def treats(d, rng):
    items = [(apple, rng.randint(90, 120), 130) for _ in range(3)]
    items += [(icecream, rng.randint(90, 115), 150) for _ in range(3)]
    items += [(cupcake, rng.randint(90, 115), 140) for _ in range(3)]
    items += [(heart, rng.randint(60, 90), 85) for _ in range(3)]
    items += [(butterfly, 55, 75)] * 1 + [(star, 45, 60)] * 3
    placed = scatter(d, rng, items, 200, 1560)
    sprinkle(d, rng, placed, 200, 1580, 8)


def bugs(d, rng):
    items = [(ladybug, rng.randint(95, 125), 160) for _ in range(3)]
    items += [(butterfly, rng.randint(70, 90), 100) for _ in range(2)]
    items += [(mushroom, rng.randint(85, 110), 125) for _ in range(3)]
    items += [(flower, rng.randint(42, 55), 100) for _ in range(3)]
    items += [(star, 40, 55)] * 2
    placed = scatter(d, rng, items, 200, 1560)
    sprinkle(d, rng, placed, 200, 1580, 8)


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
def frame(cv, theme, n):
    cv.rectangle([0, 0, W, 180], fill=WHITE)
    cv.rectangle([0, H - 150, W, H], fill=WHITE)
    cv.rectangle([0, 0, 34, H], fill=WHITE)       # frame ke bahar kuch na dikhe
    cv.rectangle([W - 34, 0, W, H], fill=WHITE)
    cv.rounded_rectangle([28, 28, W - 28, H - 28], 50, outline=BLACK, width=9)
    cv.rounded_rectangle([48, 48, W - 48, H - 48], 36, outline=BLACK, width=3)
    cv.rounded_rectangle([150, 68, W - 150, 166], 46, fill=WHITE, outline=BLACK, width=7)
    cv.text((W // 2, 117), TITLES[theme], BLACK, 62)
    for sx in (95, W - 95):
        star(cv, sx, 117, 34, None)
    cv.line([(90, H - 150), (W - 90, H - 150)], fill=BLACK, width=3)
    cv.text((95, H - 85), "Naam: ______________", BLACK, 40, "lm")
    cv.text((W - 95, H - 85), f"Sheet No. {n:,}", BLACK, 32, "rm")


def make_page(n):
    """Sheet number n (1..TOTAL) ki sheet. Same n = hamesha same sheet."""
    theme = theme_of(n)
    rng = random.Random(n)
    cv = Canvas()
    THEMES[theme](cv, rng)
    frame(cv, theme, n)
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


if "chosen" not in st.session_state:
    st.session_state.chosen = THEME_NAMES[:]
if "view" not in st.session_state:
    st.session_state.view = SINGLE
if "sheet_no" not in st.session_state:
    cb_random()

st.title("🎨 Bacho ki Drawing Book")
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
