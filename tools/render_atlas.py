#!/usr/bin/env python3
"""Render the 1024x1024 World News Chronicle Front Page (v7, 36 pure Mon 23 Nov 2026 stories).

Playoff Chronicle Architecture (1024x1024 via 2x supersampling -> LANCZOS):
- Band 1 (y=0..62): Masthead ribbon + 37px Noto Serif 'Monday 23 November 2026' + double rule
- Band 2 (y=64..98): 'THE DAY IN UTC' chronological timeline with 6 verified 23 Nov milestones
- Band 3 (y=102..330): 3 Flagship Illustrated Lead Cards (326x228px) with vector art, stat plaque,
  numbered circle, verification stamp, 15.6px bold serif headline, 2-3 line factual sub-deck & sources
- Band 4 (y=336..676): 2x5 = 10 Illustrated Feature Cards (194x167px) with vector art, stat plaque,
  numbered circle 4..13, verification stamp, 12.5px bold serif headline, 2-line factual sub-deck & sources
- Band 5 (y=682..934): Bottom-left Natural Earth 110m map (278x252px, numbered pins 1-13 + region counts)
  + Bottom-right 2-column light-ivory sourced wire (#14-#36, 12 left + 11 right, single-line crisp ink + C/O/R tags)
- Band 6 (y=938..1018): Crimson-bordered DATE CHECK audit box + verification legend footer
"""

from __future__ import annotations

import json
import math
import struct
import zlib
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont

WIDTH = 1024
HEIGHT = 1024
SCALE = 2
CW = WIDTH * SCALE
CH = HEIGHT * SCALE

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_PNG = REPO_ROOT / "entry.png"
GEOJSON_PATH = Path(__file__).resolve().parent / "ne_110m_land.geojson"

# Open system fonts
SERIF_BOLD = "/usr/share/fonts/truetype/noto/NotoSerif-Bold.ttf"
SANS_BLACK = "/usr/share/fonts/truetype/lato/Lato-Black.ttf"
SANS_BOLD = "/usr/share/fonts/truetype/lato/Lato-Bold.ttf"
SANS_SEMI = "/usr/share/fonts/truetype/lato/Lato-Semibold.ttf"
SANS_REG = "/usr/share/fonts/truetype/lato/Lato-Regular.ttf"

# Pure Archival Ivory Broadsheet Palette
PAPER = "#FAF8F3"
CARD_BG = "#FFFFFF"
SOFT_PANEL = "#F3EFE5"
HAIRLINE = "#D7D0C2"
ROW_RULE = "#E7E1D5"
INK = "#0F172A"
INK_DARK = "#1E293B"
INK_MUTED = "#475569"
CRIMSON = "#B91C1C"
GOLD = "#B78727"
NAVY = "#0F1E33"

OCEAN = "#DCEAF5"
OCEAN_GRID = "#C8DCEE"
LAND_FILL = "#ECE3CE"
LAND_STROKE = "#8F826C"

REGION_COLORS = {
    "GLOBAL": "#0E7490",
    "ASIA": "#B91C1C",
    "MIDDLE_EAST": "#C2410C",
    "EUROPE": "#1D4ED8",
    "AFRICA": "#047857",
    "AMERICAS": "#4338CA",
    "S_AMERICA": "#0F766E",
    "OCEANIA": "#92400E",
}

STAMP_STYLE = {
    "CONFIRMED": ("#065F46", "#D1FAE5", "C"),
    "OFFICIAL": ("#1E40AF", "#DBEAFE", "O"),
    "REPORTED": ("#92400E", "#FEF3C7", "R"),
    "CLAIM": ("#991B1B", "#FEE2E2", "CL"),
}

BANNED_CARRYOVER_TOKENS = (
    "merkury",
    "verica",
    "verstappen",
    "alcaraz",
    "liverpool",
    "bepicolombo",
    "cop31",
    "co-op live",
    "dymer",
    "an-12",
    "bank of ghana",
    "blues",
    "bears",
    "ituri",
    "€7.9b",
)


def s(v: float) -> int:
    return int(round(v * SCALE))


def sf(v: float) -> float:
    return v * SCALE


def load_font(path: str, size_px: float) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, int(round(size_px * SCALE)))


def text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> tuple[float, float]:
    box = draw.textbbox((0, 0), text, font=font)
    return (box[2] - box[0]) / SCALE, (box[3] - box[1]) / SCALE


def draw_centered_text(
    draw: ImageDraw.ImageDraw,
    cx: float,
    cy: float,
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: str,
) -> tuple[float, float, float, float]:
    box = draw.textbbox((0, 0), text, font=font)
    tw = box[2] - box[0]
    th = box[3] - box[1]
    x = sf(cx) - tw / 2 - box[0]
    y = sf(cy) - th / 2 - box[1]
    draw.text((x, y), text, font=font, fill=fill)
    return ((x + box[0]) / SCALE, (y + box[1]) / SCALE, (x + box[2]) / SCALE, (y + box[3]) / SCALE)


def draw_left_text(
    draw: ImageDraw.ImageDraw,
    x0: float,
    cy: float,
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: str,
) -> tuple[float, float, float, float]:
    box = draw.textbbox((0, 0), text, font=font)
    th = box[3] - box[1]
    x = sf(x0) - box[0]
    y = sf(cy) - th / 2 - box[1]
    draw.text((x, y), text, font=font, fill=fill)
    return ((x + box[0]) / SCALE, (y + box[1]) / SCALE, (x + box[2]) / SCALE, (y + box[3]) / SCALE)


def draw_right_text(
    draw: ImageDraw.ImageDraw,
    x1: float,
    cy: float,
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: str,
) -> tuple[float, float, float, float]:
    box = draw.textbbox((0, 0), text, font=font)
    tw = box[2] - box[0]
    th = box[3] - box[1]
    x = sf(x1) - tw - box[0]
    y = sf(cy) - th / 2 - box[1]
    draw.text((x, y), text, font=font, fill=fill)
    return ((x + box[0]) / SCALE, (y + box[1]) / SCALE, (x + box[2]) / SCALE, (y + box[3]) / SCALE)


def rounded_rect(
    draw: ImageDraw.ImageDraw,
    rect: tuple[float, float, float, float],
    radius: float,
    fill: str | None = None,
    outline: str | None = None,
    width: float = 1.0,
) -> None:
    x0, y0, x1, y1 = rect
    draw.rounded_rectangle(
        [s(x0), s(y0), s(x1), s(y1)],
        radius=s(radius),
        fill=fill,
        outline=outline,
        width=max(1, s(width)) if outline else 0,
    )


def draw_plaque(
    draw: ImageDraw.ImageDraw,
    x1: float,
    y0: float,
    text: str,
    bg: str,
    fg: str = "#FFFFFF",
    font_px: float = 11.5,
    pad_x: float = 5.0,
    h: float = 17.0,
) -> None:
    f = load_font(SANS_BLACK, font_px)
    tw, _ = text_size(draw, text, f)
    w = tw + pad_x * 2
    rect = (x1 - w, y0, x1, y0 + h)
    rounded_rect(draw, (rect[0] - 1.0, rect[1] - 1.0, rect[2] + 1.0, rect[3] + 1.0), radius=4.2, fill="#FFFFFF")
    rounded_rect(draw, rect, radius=3.4, fill=bg)
    draw_centered_text(draw, (rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2, text, f, fg)


def draw_stamp(
    draw: ImageDraw.ImageDraw,
    x1: float,
    cy: float,
    kind: str,
    font_px: float = 9.2,
    h: float = 13.5,
) -> tuple[float, float, float, float]:
    fg, bg, _ = STAMP_STYLE[kind]
    f = load_font(SANS_BLACK, font_px)
    tw, _ = text_size(draw, kind, f)
    w = tw + 8.0
    rect = (x1 - w, cy - h / 2, x1, cy + h / 2)
    rounded_rect(draw, rect, radius=3.0, fill=bg, outline=fg, width=0.7)
    draw_centered_text(draw, (rect[0] + rect[2]) / 2, cy, kind, f, fg)
    return rect


def wrap_lines(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_w: float) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        cand = f"{cur} {w}".strip()
        tw, _ = text_size(draw, cand, font)
        if tw <= max_w or not cur:
            cur = cand
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def project_lonlat(
    lon: float,
    lat: float,
    box: tuple[float, float, float, float],
    lon_min: float = -160.0,
    lon_max: float = 180.0,
    lat_min: float = -54.0,
    lat_max: float = 75.0,
) -> tuple[float, float]:
    x0, y0, x1, y1 = box
    u = (lon - lon_min) / (lon_max - lon_min)
    v = (lat_max - lat) / (lat_max - lat_min)
    return x0 + u * (x1 - x0), y0 + v * (y1 - y0)


# ---------- BAND 2: THE DAY IN UTC TIMELINE (y=64..98px) ----------

def draw_utc_timeline(
    draw: ImageDraw.ImageDraw,
    rect: tuple[float, float, float, float],
    audit_boxes: list[tuple[str, tuple[float, float, float, float]]],
) -> None:
    x0, y0, x1, y1 = rect
    rounded_rect(draw, rect, radius=5.0, fill=SOFT_PANEL, outline=HAIRLINE, width=0.9)

    b_rect = (x0 + 4, y0 + 5, x0 + 102, y1 - 5)
    rounded_rect(draw, b_rect, radius=3.8, fill=NAVY)
    draw_centered_text(draw, (b_rect[0] + b_rect[2]) / 2, (b_rect[1] + b_rect[3]) / 2, "THE DAY IN UTC", load_font(SANS_BLACK, 10.6), "#F5D78E")

    milestones = [
        ("01:00Z", "Asia AI rout & curbs", REGION_COLORS["ASIA"]),
        ("02:41Z", "Vanuatu M6.5 quake", REGION_COLORS["OCEANIA"]),
        ("06:00Z", "Belgium flight halt", REGION_COLORS["EUROPE"]),
        ("09:00Z", "450 school hoaxes", REGION_COLORS["EUROPE"]),
        ("~10:00Z", "Ariane 6 VA271 hold", REGION_COLORS["S_AMERICA"]),
        ("12:12Z", "Spain amnesty ruling", REGION_COLORS["EUROPE"]),
    ]

    tx0 = x0 + 108
    tx1 = x1 - 6
    slot_w = (tx1 - tx0) / len(milestones)
    dot_y = y0 + 11.0
    draw.line([s(tx0 + 28), s(dot_y), s(tx1 - 28), s(dot_y)], fill="#BDB4A4", width=s(1.4))

    f_time = load_font(SANS_BLACK, 10.2)
    f_desc = load_font(SANS_BOLD, 10.8)

    for i, (utc, desc, col) in enumerate(milestones):
        sx0 = tx0 + i * slot_w
        cx = sx0 + slot_w / 2
        prect = (cx - 28, y0 + 3.5, cx + 28, y0 + 17.5)
        rounded_rect(draw, prect, radius=3.5, fill=col)
        draw_centered_text(draw, cx, y0 + 10.5, utc, f_time, "#FFFFFF")
        db = draw_centered_text(draw, cx, y1 - 8.0, desc, f_desc, INK)
        assert db[0] >= sx0 + 1.0 and db[2] <= sx0 + slot_w - 1.0, f"Timeline clipped: '{desc}'"
        audit_boxes.append((f"tl:{utc}", db))


# ---------- 3 FLAGSHIP LEAD VECTOR ILLUSTRATIONS (314 x 96px) ----------

def art_lead_asia(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float]) -> None:
    x0, y0, x1, y1 = box
    rounded_rect(draw, box, radius=5, fill="#FEF2F2", outline="#FECACA", width=1.0)
    draw.rectangle([s(x0 + 2), s(y1 - 24), s(x1 - 2), s(y1 - 2)], fill="#FDE8E8")
    for sx, sh, sw in [(x0 + 12, 26, 16), (x0 + 32, 38, 15), (x0 + 52, 46, 18), (x0 + 75, 32, 16), (x0 + 96, 40, 15)]:
        draw.rectangle([s(sx), s(y1 - 2 - sh), s(sx + sw), s(y1 - 2)], fill="#E5BEBE")
    bars = [(x0 + 24, y0 + 16, 12, 18, "#DC2626"), (x0 + 52, y0 + 24, 12, 22, "#DC2626"), (x0 + 80, y0 + 35, 12, 25, "#B91C1C"), (x0 + 108, y0 + 46, 12, 28, "#991B1B"), (x0 + 136, y0 + 55, 12, 26, "#7F1D1D")]
    for bx, by, bw, bh, col in bars:
        draw.line([s(bx + bw / 2), s(by - 6), s(bx + bw / 2), s(by + bh + 6)], fill=col, width=s(1.6))
        draw.rectangle([s(bx), s(by), s(bx + bw), s(by + bh)], fill=col)
    draw.line([(s(x0 + 18), s(y0 + 16)), (s(x0 + 86), s(y0 + 38)), (s(x0 + 114), s(y0 + 31)), (s(x0 + 178), s(y1 - 14))], fill="#7F1D1D", width=s(3.6))
    scx, scy = x1 - 54, y1 - 34
    shield = [(s(scx), s(scy - 22)), (s(scx + 20), s(scy - 15)), (s(scx + 17), s(scy + 6)), (s(scx), s(scy + 22)), (s(scx - 17), s(scy + 6)), (s(scx - 20), s(scy - 15))]
    draw.polygon(shield, fill=NAVY)
    draw.line(shield + [shield[0]], fill="#EAB308", width=s(2.2))
    draw.line([(s(scx - 8), s(scy + 1)), (s(scx - 2), s(scy + 8)), (s(scx + 9), s(scy - 6))], fill="#FACC15", width=s(3.2))
    draw_plaque(draw, x1 - 6, y0 + 5, "-3.3% · $8B", "#B91C1C", font_px=11.5, h=18.0)


def art_lead_iran(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float]) -> None:
    x0, y0, x1, y1 = box
    h = y1 - y0
    rounded_rect(draw, box, radius=5, fill="#FFF4E6", outline="#FED7AA", width=1.0)
    draw.ellipse([s(x0 + 14), s(y0 + 9), s(x0 + 36), s(y0 + 31)], fill="#FB923C")
    sea_y = y0 + h * 0.56
    rounded_rect(draw, (x0 + 1, sea_y, x1 - 1, y1 - 1), radius=4, fill="#1E3A5F")
    draw.rectangle([s(x0 + 1), s(sea_y), s(x1 - 1), s(sea_y + 8)], fill="#1E3A5F")
    for wy, wx0, wx1 in [(sea_y + 12, x0 + 18, x0 + 95), (sea_y + 24, x0 + 110, x0 + 210), (sea_y + 15, x0 + 220, x1 - 18)]:
        draw.line([s(wx0), s(wy), s(wx1), s(wy)], fill="#60A5FA", width=s(2.0))
    hull = [(s(x0 + 26), s(sea_y + 5)), (s(x0 + 146), s(sea_y + 5)), (s(x0 + 160), s(sea_y - 11)), (s(x0 + 32), s(sea_y - 11))]
    draw.polygon(hull, fill="#0F172A")
    draw.rectangle([s(x0 + 36), s(sea_y - 16), s(x0 + 144), s(sea_y - 10)], fill="#DC2626")
    draw.rectangle([s(x0 + 44), s(sea_y - 31), s(x0 + 68), s(sea_y - 16)], fill="#F8FAFC", outline="#0F172A", width=s(1.3))
    bcx, bcy = x0 + 216, sea_y - 10
    draw.arc([s(bcx - 24), s(bcy - 24), s(bcx + 24), s(bcy + 24)], start=115, end=245, fill="#DC2626", width=s(3.4))
    draw.ellipse([s(bcx - 15), s(bcy - 15), s(bcx + 15), s(bcy + 15)], fill="#DC2626", outline="#FFFFFF", width=s(2.0))
    draw.rectangle([s(bcx - 8), s(bcy - 2.8), s(bcx + 8), s(bcy + 2.8)], fill="#FFFFFF")
    draw_plaque(draw, x1 - 6, y0 + 5, "HORMUZ", "#C2410C", font_px=11.5, h=18.0)


def art_lead_spain(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float]) -> None:
    x0, y0, x1, y1 = box
    rounded_rect(draw, box, radius=5, fill="#EFF6FF", outline="#BFDBFE", width=1.0)
    base_y = y1 - 9
    draw.rectangle([s(x0 + 16), s(base_y), s(x0 + 124), s(base_y + 5)], fill="#1E3A8A")
    draw.polygon([(s(x0 + 14), s(y0 + 32)), (s(x0 + 70), s(y0 + 11)), (s(x0 + 126), s(y0 + 32))], fill="#1D4ED8")
    for cx in (x0 + 26, x0 + 48, x0 + 70, x0 + 92, x0 + 114):
        draw.rectangle([s(cx - 4.5), s(y0 + 32), s(cx + 4.5), s(base_y)], fill="#93C5FD", outline="#1D4ED8", width=s(1.0))
    gx, gy = x0 + 194, y0 + 52
    rounded_rect(draw, (gx - 26, gy + 16, gx + 26, gy + 26), radius=3, fill="#78350F")
    draw.line([s(gx - 6), s(gy - 12), s(gx + 28), s(gy + 12)], fill="#92400E", width=s(5.5))
    rounded_rect(draw, (gx - 24, gy - 26, gx + 10, gy - 4), radius=4, fill="#B45309", outline="#78350F", width=s(1.6))
    sx, sy = x1 - 36, y1 - 28
    draw.ellipse([s(sx - 17), s(sy - 17), s(sx + 17), s(sy + 17)], fill="#059669", outline="#FFFFFF", width=s(2.0))
    draw.line([(s(sx - 7), s(sy + 1)), (s(sx - 2), s(sy + 6)), (s(sx + 8), s(sy - 6))], fill="#FFFFFF", width=s(3.0))
    draw_plaque(draw, x1 - 6, y0 + 5, "AMNESTY", "#1D4ED8", font_px=11.5, h=18.0)


# ---------- 10 FEATURE CARD VECTOR ILLUSTRATIONS (184 x 58px) ----------

def art_f_cricket(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float]) -> None:
    x0, y0, x1, y1 = box
    rounded_rect(draw, box, radius=4.5, fill="#ECFDF5", outline="#A7F3D0", width=0.9)
    # Lush green Wellington oval outfield + sandy Test pitch strip
    draw.rectangle([s(x0 + 2), s(y1 - 20), s(x1 - 2), s(y1 - 2)], fill="#15803D")
    draw.polygon([(s(x0 + 16), s(y1 - 4)), (s(x0 + 36), s(y1 - 20)), (s(x0 + 82), s(y1 - 20)), (s(x0 + 102), s(y1 - 4))], fill="#E5C992")
    # Three golden cricket stumps + bails
    for sx in (x0 + 48, x0 + 57, x0 + 66):
        draw.rectangle([s(sx - 1.8), s(y0 + 14), s(sx + 1.8), s(y1 - 12)], fill="#D97706", outline="#92400E", width=s(0.8))
    draw.line([s(x0 + 46), s(y0 + 13), s(x0 + 68), s(y0 + 13)], fill="#B45309", width=s(2.4))
    # Red cricket ball with white seam
    bx, by = x0 + 96, y0 + 26
    draw.ellipse([s(bx - 9), s(by - 9), s(bx + 9), s(by + 9)], fill="#B91C1C", outline="#7F1D1D", width=s(1.0))
    draw.arc([s(bx - 7), s(by - 6), s(bx + 7), s(by + 6)], start=210, end=330, fill="#F8FAFC", width=s(1.4))
    # Dark stadium scoreboard on right
    rounded_rect(draw, (x0 + 114, y0 + 23, x1 - 6, y1 - 10), radius=3.5, fill=NAVY, outline="#334155", width=s(1.0))
    draw_centered_text(draw, (x0 + 114 + x1 - 6) / 2, (y0 + 23 + y1 - 10) / 2, "DAY 5", load_font(SANS_BLACK, 10.5), "#FACC15")
    draw_plaque(draw, x1 - 4, y0 + 4, "TEST DRAW", "#92400E", font_px=9.8, h=15.5)


def art_f_gas(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float]) -> None:
    x0, y0, x1, y1 = box
    mid = x0 + 64
    rounded_rect(draw, box, radius=4.5, fill="#FEF3C7", outline="#FDE68A", width=0.9)
    draw.rectangle([s(x0 + 1), s(y0 + 1), s(mid), s(y1 - 1)], fill="#DBEAFE")
    cx, cy, r = x0 + 22, y0 + 26, 11.0
    for deg in range(0, 360, 60):
        rad = math.radians(deg)
        draw.line([s(cx), s(cy), s(cx + math.cos(rad) * r), s(cy + math.sin(rad) * r)], fill="#1D4ED8", width=s(2.0))
    draw.rectangle([s(x0 + 38), s(y1 - 24), s(x0 + 54), s(y1 - 2)], fill="#60A5FA")
    draw.polygon([(s(x0 + 36), s(y1 - 24)), (s(x0 + 46), s(y1 - 33)), (s(x0 + 56), s(y1 - 24))], fill="#1E40AF")
    fx, fy = mid + 24, y1 - 5
    draw.polygon([(s(fx), s(y0 + 10)), (s(fx + 13), s(y0 + 30)), (s(fx + 10), s(fy)), (s(fx - 10), s(fy)), (s(fx - 13), s(y0 + 30))], fill="#EA580C")
    draw.polygon([(s(fx), s(y0 + 23)), (s(fx + 6), s(y0 + 38)), (s(fx + 5), s(fy)), (s(fx - 5), s(fy)), (s(fx - 6), s(y0 + 38))], fill="#FACC15")
    draw.line([(s(mid + 44), s(y1 - 10)), (s(mid + 64), s(y1 - 22)), (s(x1 - 22), s(y0 + 24))], fill="#DC2626", width=s(2.8))
    draw_plaque(draw, x1 - 4, y0 + 4, "+6% €93", "#1D4ED8", font_px=10.2, h=15.5)


def art_f_belgium(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float]) -> None:
    x0, y0, x1, y1 = box
    rounded_rect(draw, box, radius=4.5, fill="#EFF6FF", outline="#BFDBFE", width=0.9)
    draw.rectangle([s(x0 + 4), s(y1 - 13), s(x1 - 4), s(y1 - 3)], fill="#334155")
    for rx in range(int(x0 + 14), int(x1 - 14), 24):
        draw.line([s(rx), s(y1 - 8), s(rx + 12), s(y1 - 8)], fill="#F8FAFC", width=s(1.6))
    py = y1 - 22
    rounded_rect(draw, (x0 + 20, py - 5, x0 + 82, py + 4), radius=4, fill="#1E3A8A")
    draw.polygon([(s(x0 + 24), s(py - 5)), (s(x0 + 18), s(py - 18)), (s(x0 + 34), s(py - 5))], fill="#2563EB")
    draw.polygon([(s(x0 + 46), s(py)), (s(x0 + 34), s(py + 10)), (s(x0 + 62), s(py))], fill="#3B82F6")
    cx, cy = x0 + 114, y0 + 30
    draw.ellipse([s(cx - 14), s(cy - 14), s(cx + 14), s(cy + 14)], fill="#DC2626", outline="#FFFFFF", width=s(1.8))
    draw.rectangle([s(cx - 7), s(cy - 2.5), s(cx + 7), s(cy + 2.5)], fill="#FFFFFF")
    draw_plaque(draw, x1 - 4, y0 + 4, "ATC HALT", "#1D4ED8", font_px=10.0, h=15.5)


def art_f_schools(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float]) -> None:
    x0, y0, x1, y1 = box
    rounded_rect(draw, box, radius=4.5, fill="#FEF2F2", outline="#FECACA", width=0.9)
    draw.rectangle([s(x0 + 12), s(y0 + 24), s(x0 + 70), s(y1 - 5)], fill="#CBD5E1", outline="#475569", width=s(1.2))
    draw.polygon([(s(x0 + 9), s(y0 + 24)), (s(x0 + 41), s(y0 + 10)), (s(x0 + 73), s(y0 + 24))], fill="#991B1B")
    for wx in (x0 + 20, x0 + 37, x0 + 54):
        draw.rectangle([s(wx), s(y0 + 30), s(wx + 9), s(y0 + 40)], fill="#3B82F6")
    ex0, ey0, ex1, ey1 = x0 + 82, y0 + 24, x0 + 132, y1 - 8
    rounded_rect(draw, (ex0, ey0, ex1, ey1), radius=3, fill="#FFFFFF", outline="#B91C1C", width=s(1.6))
    draw.line([(s(ex0 + 2), s(ey0 + 2)), (s((ex0 + ex1) / 2), s(ey0 + 15)), (s(ex1 - 2), s(ey0 + 2))], fill="#B91C1C", width=s(1.6))
    tx, ty = x0 + 128, y0 + 42
    draw.polygon([(s(tx), s(ty - 11)), (s(tx + 11), s(ty + 8)), (s(tx - 11), s(ty + 8))], fill="#F59E0B", outline="#92400E")
    draw_plaque(draw, x1 - 4, y0 + 4, "450 HOAXES", "#B91C1C", font_px=9.6, h=15.5)


def art_f_libya(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float]) -> None:
    x0, y0, x1, y1 = box
    rounded_rect(draw, box, radius=4.5, fill="#FEF3C7", outline="#FDE68A", width=0.9)
    draw.polygon([(s(x0 + 1), s(y1 - 1)), (s(x0 + 1), s(y1 - 15)), (s(x0 + 68), s(y1 - 24)), (s(x1 - 1), s(y1 - 14)), (s(x1 - 1), s(y1 - 1))], fill="#E5C992")
    py = (y0 + y1) / 2 + 2
    draw.rectangle([s(x0 + 8), s(py - 5), s(x1 - 46), s(py + 5)], fill="#475569", outline="#1E293B", width=s(1.2))
    vcx, vcy = x0 + 62, py
    draw.ellipse([s(vcx - 16), s(vcy - 16), s(vcx + 16), s(vcy + 16)], fill="#FFFFFF", outline="#DC2626", width=s(3.4))
    for deg in (0, 60, 120):
        rad = math.radians(deg)
        draw.line([s(vcx - math.cos(rad) * 13), s(vcy - math.sin(rad) * 13), s(vcx + math.cos(rad) * 13), s(vcy + math.sin(rad) * 13)], fill="#DC2626", width=s(2.2))
    dx, dy = x1 - 30, py + 10
    draw.polygon([(s(dx), s(dy - 10)), (s(dx + 6.5), s(dy + 2)), (s(dx), s(dy + 8)), (s(dx - 6.5), s(dy + 2))], fill="#0F172A")
    draw_plaque(draw, x1 - 4, y0 + 4, "-350K BPD", "#047857", font_px=9.8, h=15.5)


def art_f_cphia(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float]) -> None:
    x0, y0, x1, y1 = box
    rounded_rect(draw, box, radius=4.5, fill="#ECFDF5", outline="#A7F3D0", width=0.9)
    cy = (y0 + y1) / 2 + 2
    cx = x0 + 36
    draw.ellipse([s(cx - 19), s(cy - 19), s(cx + 19), s(cy + 19)], fill="#047857", outline="#065F46", width=s(1.8))
    draw.rectangle([s(cx - 4.5), s(cy - 11.5), s(cx + 4.5), s(cy + 11.5)], fill="#FFFFFF")
    draw.rectangle([s(cx - 11.5), s(cy - 4.5), s(cx + 11.5), s(cy + 4.5)], fill="#FFFFFF")
    for i in range(3):
        vx0 = x0 + 68 + i * 22
        rounded_rect(draw, (vx0, y0 + 22, vx0 + 15, y1 - 6), radius=3, fill="#FFFFFF", outline="#047857", width=s(1.5))
        draw.rectangle([s(vx0 + 2), s(y0 + 34), s(vx0 + 13), s(y1 - 8)], fill="#34D399")
        draw.rectangle([s(vx0 + 3), s(y0 + 16), s(vx0 + 12), s(y0 + 22)], fill="#065F46")
    draw_plaque(draw, x1 - 4, y0 + 4, "60% GOAL", "#047857", font_px=9.8, h=15.5)


def art_f_tides(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float]) -> None:
    x0, y0, x1, y1 = box
    rounded_rect(draw, box, radius=4.5, fill="#EEF2FF", outline="#C7D2FE", width=0.9)
    draw.rectangle([s(x0 + 22), s(y0 + 10), s(x0 + 28), s(y1 - 14)], fill="#DC2626")
    draw.rectangle([s(x0 + 82), s(y0 + 10), s(x0 + 88), s(y1 - 14)], fill="#DC2626")
    draw.line([s(x0 + 6), s(y1 - 24), s(x0 + 112), s(y1 - 24)], fill="#B91C1C", width=s(2.6))
    draw.arc([s(x0 + 25), s(y0 + 2), s(x0 + 85), s(y0 + 36)], start=0, end=180, fill="#DC2626", width=s(1.8))
    draw.rectangle([s(x0 + 1), s(y1 - 18), s(x1 - 1), s(y1 - 1)], fill="#1D4ED8")
    for wx in range(int(x0 + 8), int(x1 - 16), 24):
        draw.arc([s(wx), s(y1 - 25), s(wx + 22), s(y1 - 11)], start=180, end=360, fill="#3B82F6", width=s(2.4))
    draw.ellipse([s(x0 + 104), s(y0 + 18), s(x0 + 136), s(y0 + 31)], fill="#64748B")
    for rx in (x0 + 111, x0 + 120, x0 + 129):
        draw.line([s(rx), s(y0 + 33), s(rx - 3.5), s(y0 + 40)], fill="#2563EB", width=s(1.6))
    draw_plaque(draw, x1 - 4, y0 + 4, "KING TIDES", "#4338CA", font_px=9.6, h=15.5)


def art_f_ariane(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float]) -> None:
    x0, y0, x1, y1 = box
    rounded_rect(draw, box, radius=4.5, fill="#F0FDFA", outline="#99F6E4", width=0.9)
    draw.rectangle([s(x0 + 10), s(y1 - 9), s(x0 + 108), s(y1 - 3)], fill="#334155")
    draw.rectangle([s(x0 + 24), s(y0 + 12), s(x0 + 32), s(y1 - 9)], fill="#64748B")
    draw.line([s(x0 + 32), s(y0 + 24), s(x0 + 54), s(y0 + 24)], fill="#475569", width=s(2.0))
    rx = x0 + 62
    draw.polygon([(s(rx), s(y0 + 6)), (s(rx + 7), s(y0 + 18)), (s(rx - 7), s(y0 + 18))], fill="#0F766E")
    draw.rectangle([s(rx - 7), s(y0 + 18), s(rx + 7), s(y1 - 10)], fill="#FFFFFF", outline="#0F172A", width=s(1.3))
    draw.rectangle([s(rx - 13), s(y0 + 29), s(rx - 7), s(y1 - 9)], fill="#0D9488")
    draw.rectangle([s(rx + 7), s(y0 + 29), s(rx + 13), s(y1 - 9)], fill="#0D9488")
    hx, hy = x0 + 114, y0 + 34
    draw.ellipse([s(hx - 14), s(hy - 14), s(hx + 14), s(hy + 14)], fill="#DC2626", outline="#FFFFFF", width=s(1.8))
    draw.rectangle([s(hx - 5), s(hy - 7), s(hx - 1.5), s(hy + 7)], fill="#FFFFFF")
    draw.rectangle([s(hx + 1.5), s(hy - 7), s(hx + 5), s(hy + 7)], fill="#FFFFFF")
    draw_plaque(draw, x1 - 4, y0 + 4, "36 SATS", "#0F766E", font_px=10.2, h=15.5)


def art_f_heart(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float]) -> None:
    x0, y0, x1, y1 = box
    rounded_rect(draw, box, radius=4.5, fill="#ECFEFF", outline="#A5F3FC", width=0.9)
    mx0, my0, mx1, my1 = x0 + 7, y0 + 6, x1 - 66, y1 - 6
    rounded_rect(draw, (mx0, my0, mx1, my1), radius=5, fill="#0F172A", outline="#0E7490", width=s(1.5))
    ey = (my0 + my1) / 2 + 2
    pts = [(mx0 + 6, ey), (mx0 + 26, ey), (mx0 + 32, ey - 7), (mx0 + 38, ey + 6), (mx0 + 45, ey - 18), (mx0 + 53, ey + 13), (mx0 + 60, ey - 4), (mx0 + 72, ey), (mx1 - 6, ey)]
    draw.line([(s(px), s(py)) for px, py in pts], fill="#22D3EE", width=s(2.4))
    hx, hy = x1 - 36, y1 - 20
    draw.ellipse([s(hx - 9), s(hy - 7), s(hx + 1), s(hy + 3)], fill="#EF4444")
    draw.ellipse([s(hx - 1), s(hy - 7), s(hx + 9), s(hy + 3)], fill="#EF4444")
    draw.polygon([(s(hx - 8.5), s(hy + 0.5)), (s(hx + 8.5), s(hy + 0.5)), (s(hx), s(hy + 11))], fill="#EF4444")
    draw_plaque(draw, x1 - 4, y0 + 4, "PHASE III", "#0E7490", font_px=10.0, h=15.5)


def art_f_quake(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float]) -> None:
    x0, y0, x1, y1 = box
    rounded_rect(draw, box, radius=4.5, fill="#FFFBEB", outline="#FDE68A", width=0.9)
    cx, cy = x0 + 44, (y0 + y1) / 2 + 2
    for r, col in [(22, "#F59E0B"), (15, "#EA580C"), (8, "#DC2626")]:
        draw.ellipse([s(cx - r), s(cy - r), s(cx + r), s(cy + r)], outline=col, width=s(2.2))
    draw.ellipse([s(cx - 4), s(cy - 4), s(cx + 4), s(cy + 4)], fill="#991B1B")
    sy = y0 + 36
    pts = [(x0 + 76, sy), (x0 + 90, sy), (x0 + 97, sy - 11), (x0 + 104, sy + 13), (x0 + 112, sy - 16), (x0 + 120, sy + 14), (x0 + 128, sy - 8), (x0 + 136, sy + 5), (x1 - 8, sy)]
    draw.line([(s(px), s(py)) for px, py in pts], fill="#92400E", width=s(2.2))
    draw_plaque(draw, x1 - 4, y0 + 4, "M6.5", "#92400E", font_px=10.8, h=15.5)


# ---------- BAND 3 & 4 CARD RENDERERS ----------

def draw_lead_card(
    draw: ImageDraw.ImageDraw,
    rect: tuple[float, float, float, float],
    num: int,
    kicker: str,
    stamp: str,
    color: str,
    headline: str,
    deck: str,
    source: str,
    art_fn: Any,
    audit_boxes: list[tuple[str, tuple[float, float, float, float]]],
) -> None:
    x0, y0, x1, y1 = rect
    rounded_rect(draw, rect, radius=6.0, fill=CARD_BG, outline=HAIRLINE, width=1.0)
    draw.rectangle([s(x0 + 6), s(y0 + 1), s(x1 - 6), s(y0 + 3.5)], fill=color)

    art_box = (x0 + 6, y0 + 7, x1 - 6, y0 + 103)
    art_fn(draw, art_box)

    my = y0 + 114.5
    draw.ellipse([s(x0 + 7), s(my - 7.5), s(x0 + 22), s(my + 7.5)], fill=color)
    draw_centered_text(draw, x0 + 14.5, my, str(num), load_font(SANS_BLACK, 10.4), "#FFFFFF")
    kb = draw_left_text(draw, x0 + 26, my, kicker, load_font(SANS_BLACK, 10.6), color)
    sb = draw_stamp(draw, x1 - 7, my, stamp, font_px=9.0, h=13.5)
    assert kb[2] + 4.0 <= sb[0], f"Lead meta overlap: {kicker}"

    max_w = x1 - x0 - 15.0
    hf = load_font(SERIF_BOLD, 15.6)
    hlines = wrap_lines(draw, headline, hf, max_w)
    assert len(hlines) <= 2, f"Lead headline >2 lines ({hlines}): {headline}"
    hy = y0 + 133.5
    for i, ln in enumerate(hlines):
        hb = draw_left_text(draw, x0 + 7.5, hy + i * 19.0, ln, hf, INK)
        assert hb[2] <= x1 - 5.0, f"Lead headline overflow: {ln}"
        audit_boxes.append((f"lead_h:{num}:{i}", hb))

    df = load_font(SANS_SEMI, 11.4)
    dlines = wrap_lines(draw, deck, df, max_w)
    assert len(dlines) <= 3, f"Lead deck >3 lines ({dlines}): {deck}"
    dy = hy + len(hlines) * 19.0 + 3.5
    for i, ln in enumerate(dlines):
        db = draw_left_text(draw, x0 + 7.5, dy + i * 14.0, ln, df, INK_DARK)
        assert db[2] <= x1 - 5.0 and db[3] <= y1 - 15.5, f"Lead deck overflow: {ln}"
        audit_boxes.append((f"lead_d:{num}:{i}", db))

    src_b = draw_left_text(draw, x0 + 7.5, y1 - 9.0, f"Source: {source}", load_font(SANS_BOLD, 9.8), INK_MUTED)
    audit_boxes.append((f"lead_s:{num}", src_b))


def draw_feature_card(
    draw: ImageDraw.ImageDraw,
    rect: tuple[float, float, float, float],
    num: int,
    kicker: str,
    stamp: str,
    color: str,
    headline: str,
    deck: str,
    source: str,
    art_fn: Any,
    audit_boxes: list[tuple[str, tuple[float, float, float, float]]],
) -> None:
    x0, y0, x1, y1 = rect
    rounded_rect(draw, rect, radius=5.5, fill=CARD_BG, outline=HAIRLINE, width=0.9)
    draw.rectangle([s(x0 + 5), s(y0 + 1), s(x1 - 5), s(y0 + 3.2)], fill=color)

    art_box = (x0 + 5, y0 + 6, x1 - 5, y0 + 64)
    art_fn(draw, art_box)

    my = y0 + 74.5
    draw.ellipse([s(x0 + 5.5), s(my - 6.8), s(x0 + 19.1), s(my + 6.8)], fill=color)
    draw_centered_text(draw, x0 + 12.3, my, str(num), load_font(SANS_BLACK, 9.6), "#FFFFFF")
    kb = draw_left_text(draw, x0 + 22.0, my, kicker, load_font(SANS_BLACK, 9.6), color)
    sb = draw_stamp(draw, x1 - 5.5, my, stamp, font_px=8.2, h=12.5)
    assert kb[2] + 3.0 <= sb[0], f"Feature meta overlap ({num}): {kicker} vs {stamp}"

    max_w = x1 - x0 - 11.5
    hf = load_font(SERIF_BOLD, 12.5)
    hlines = wrap_lines(draw, headline, hf, max_w)
    assert len(hlines) <= 2, f"Feature headline >2 lines ({num}, {hlines}): {headline}"
    hy = y0 + 91.5
    for i, ln in enumerate(hlines):
        hb = draw_left_text(draw, x0 + 5.8, hy + i * 15.0, ln, hf, INK)
        assert hb[2] <= x1 - 4.0, f"Feature headline overflow ({num}): {ln}"
        audit_boxes.append((f"feat_h:{num}:{i}", hb))

    df = load_font(SANS_SEMI, 10.6)
    dlines = wrap_lines(draw, deck, df, max_w)
    assert len(dlines) <= 3, f"Feature deck >3 lines ({num}, {dlines}): {deck}"
    dy = hy + len(hlines) * 15.0 + 3.0
    for i, ln in enumerate(dlines):
        db = draw_left_text(draw, x0 + 5.8, dy + i * 12.6, ln, df, INK_DARK)
        assert db[2] <= x1 - 4.0 and db[3] <= y1 - 13.5, f"Feature deck overflow ({num}): {ln}"
        audit_boxes.append((f"feat_d:{num}:{i}", db))

    src_b = draw_left_text(draw, x0 + 5.8, y1 - 7.8, source, load_font(SANS_BOLD, 9.4), INK_MUTED)
    audit_boxes.append((f"feat_s:{num}", src_b))


# ---------- BAND 5A: BOTTOM-LEFT NATURAL EARTH MAP (x=12..290, y=682..934) ----------

def draw_compact_map(
    draw: ImageDraw.ImageDraw,
    panel: tuple[float, float, float, float],
    audit_boxes: list[tuple[str, tuple[float, float, float, float]]],
) -> None:
    x0, y0, x1, y1 = panel
    hdr_h = 20.0
    ftr_h = 34.0
    rounded_rect(draw, panel, radius=6.0, fill=CARD_BG, outline=HAIRLINE, width=1.0)

    draw_left_text(draw, x0 + 8, y0 + hdr_h / 2 + 1, "WHERE IT HAPPENED", load_font(SANS_BLACK, 11.2), INK)
    draw_right_text(draw, x1 - 8, y0 + hdr_h / 2 + 1, "1–13 = CARDS", load_font(SANS_BOLD, 9.6), INK_MUTED)
    draw.line([s(x0 + 6), s(y0 + hdr_h), s(x1 - 6), s(y0 + hdr_h)], fill=ROW_RULE, width=s(1.0))

    map_box = (x0 + 5, y0 + hdr_h + 3, x1 - 5, y1 - ftr_h - 2)
    mx0, my0, mx1, my1 = map_box
    rounded_rect(draw, map_box, radius=4.5, fill=OCEAN, outline="#B8D0E4", width=0.8)

    for lon in range(-120, 180, 60):
        gx, _ = project_lonlat(lon, 0, map_box)
        draw.line([s(gx), s(my0 + 2), s(gx), s(my1 - 2)], fill=OCEAN_GRID, width=1)
    for lat in (-30, 0, 30, 60):
        _, gy = project_lonlat(0, lat, map_box)
        draw.line([s(mx0 + 2), s(gy), s(mx1 - 2), s(gy)], fill=OCEAN_GRID, width=1)

    assert GEOJSON_PATH.exists(), f"Missing bundled Natural Earth land GeoJSON: {GEOJSON_PATH}"
    geo = json.loads(GEOJSON_PATH.read_text(encoding="utf-8"))
    for feat in geo.get("features", []):
        geom = feat.get("geometry", {})
        gtype = geom.get("type")
        coords = geom.get("coordinates", [])
        polys = [coords] if gtype == "Polygon" else (coords if gtype == "MultiPolygon" else [])
        for poly in polys:
            if not poly:
                continue
            pts: list[tuple[int, int]] = []
            for lon, lat in poly[0]:
                if lat < -54.0:
                    continue
                clon = max(-160.0, min(180.0, lon))
                clat = max(-54.0, min(75.0, lat))
                px, py = project_lonlat(clon, clat, map_box)
                pts.append((s(px), s(py)))
            if len(pts) >= 3:
                draw.polygon(pts, fill=LAND_FILL, outline=LAND_STROKE)

    wire_dots = [
        (-77.0, 38.9, REGION_COLORS["AMERICAS"]),   # US Fed
        (-73.6, 45.5, REGION_COLORS["AMERICAS"]),   # Montreal
        (-76.6, 5.7, REGION_COLORS["S_AMERICA"]),   # Colombia
        (-59.5, -51.7, REGION_COLORS["S_AMERICA"]), # Falklands
        (-0.1, 51.5, REGION_COLORS["EUROPE"]),      # London
        (139.7, 35.7, REGION_COLORS["ASIA"]),       # Tokyo
        (103.8, 1.3, REGION_COLORS["ASIA"]),        # Singapore
        (77.2, 28.6, REGION_COLORS["ASIA"]),        # Delhi
        (34.4, 31.5, REGION_COLORS["MIDDLE_EAST"]), # Gaza
        (46.7, 24.7, REGION_COLORS["MIDDLE_EAST"]), # Riyadh
        (-4.0, 5.3, REGION_COLORS["AFRICA"]),       # Abidjan
        (31.0, -29.8, REGION_COLORS["AFRICA"]),     # Durban water summit
        (28.0, -15.4, REGION_COLORS["AFRICA"]),     # Zambia customs link
        (149.1, -35.3, REGION_COLORS["OCEANIA"]),   # Australia
    ]
    for lon, lat, col in wire_dots:
        px, py = project_lonlat(lon, lat, map_box)
        draw.ellipse([s(px - 2.6), s(py - 2.6), s(px + 2.6), s(py + 2.6)], fill=col, outline="#FFFFFF", width=s(0.6))

    pins = [
        ("1", 126.9, 36.5, 0, 0, REGION_COLORS["ASIA"]),
        ("2", 56.3, 26.5, 0, 0, REGION_COLORS["MIDDLE_EAST"]),
        ("3", -3.7, 40.4, -7, 4, REGION_COLORS["EUROPE"]),
        ("4", 174.8, -41.3, -6, 0, REGION_COLORS["OCEANIA"]),
        ("5", 4.9, 52.3, -4, -12, REGION_COLORS["EUROPE"]),
        ("6", 4.3, 50.8, 4, 6, REGION_COLORS["EUROPE"]),
        ("7", 11.5, 51.2, 13, -10, REGION_COLORS["EUROPE"]),
        ("8", 12.2, 26.5, 0, 0, REGION_COLORS["AFRICA"]),
        ("9", 38.7, 9.0, 0, 0, REGION_COLORS["AFRICA"]),
        ("10", -122.4, 37.8, 0, 0, REGION_COLORS["AMERICAS"]),
        ("11", -52.7, 5.2, 0, 0, REGION_COLORS["S_AMERICA"]),
        ("12", 7.6, 47.6, -15, 2, REGION_COLORS["GLOBAL"]),
        ("13", 168.3, -17.7, -7, 0, REGION_COLORS["OCEANIA"]),
    ]
    pf = load_font(SANS_BLACK, 8.8)
    for num, lon, lat, dx, dy, col in pins:
        px, py = project_lonlat(lon, lat, map_box)
        cx, cy = px + dx, py + dy
        if dx or dy:
            draw.line([s(px), s(py), s(cx), s(cy)], fill=INK, width=s(0.9))
        r = 6.2
        draw.ellipse([s(cx - r), s(cy - r), s(cx + r), s(cy + r)], fill=col, outline="#FFFFFF", width=s(1.2))
        draw_centered_text(draw, cx, cy, num, pf, "#FFFFFF")

    fy = y1 - ftr_h + 1
    draw.line([s(x0 + 6), s(fy), s(x1 - 6), s(fy)], fill=ROW_RULE, width=s(0.9))
    rf = load_font(SANS_BLACK, 10.4)
    draw_centered_text(draw, (x0 + x1) / 2, fy + 10.5, "Europe 9 · Asia 6 · Americas 6 · Africa 5", rf, INK)
    draw_centered_text(draw, (x0 + x1) / 2, fy + 24.5, "Middle East 4 · Oceania 3 · Global 3 (36 total)", rf, INK)


# ---------- BAND 5B: 2-COLUMN LIGHT-IVORY WIRE (#14-#36, x=298..1012, y=682..934) ----------

def draw_ivory_wire(
    draw: ImageDraw.ImageDraw,
    panel: tuple[float, float, float, float],
    left_items: list[tuple[int, str, str, str, str]],
    right_items: list[tuple[int, str, str, str, str]],
    audit_boxes: list[tuple[str, tuple[float, float, float, float]]],
) -> None:
    x0, y0, x1, y1 = panel
    hdr_h = 20.0
    rounded_rect(draw, panel, radius=6.0, fill=CARD_BG, outline=HAIRLINE, width=1.0)

    draw_left_text(draw, x0 + 9, y0 + hdr_h / 2 + 1, "ALSO ON MONDAY 23 NOVEMBER  (23 MORE VERIFIED STORIES)", load_font(SANS_BLACK, 11.2), INK)
    draw_right_text(draw, x1 - 9, y0 + hdr_h / 2 + 1, "C=CONFIRMED · O=OFFICIAL · R=REPORTED", load_font(SANS_BOLD, 9.5), INK_MUTED)
    draw.line([s(x0 + 6), s(y0 + hdr_h), s(x1 - 6), s(y0 + hdr_h)], fill=ROW_RULE, width=s(1.0))

    mid_x = (x0 + x1) / 2
    draw.line([s(mid_x), s(y0 + hdr_h + 4), s(mid_x), s(y1 - 6)], fill=ROW_RULE, width=s(1.0))

    body_y0 = y0 + hdr_h + 4.0
    row_h = (y1 - 5.0 - body_y0) / 12.0

    f_num = load_font(SANS_BOLD, 9.8)
    f_lead = load_font(SANS_BLACK, 11.0)
    f_body = load_font(SANS_SEMI, 10.8)
    f_src = load_font(SANS_BOLD, 9.6)
    f_code = load_font(SANS_BLACK, 8.8)

    for col_idx, items in enumerate((left_items, right_items)):
        cx0 = (x0 + 7.5) if col_idx == 0 else (mid_x + 7.5)
        cx1 = (mid_x - 6.5) if col_idx == 0 else (x1 - 7.5)
        for r_idx, (num, lead, body, src, stamp_kind) in enumerate(items):
            ry_top = body_y0 + r_idx * row_h
            cy = ry_top + row_h / 2
            baseline = cy + 3.6
            if r_idx > 0:
                draw.line([s(cx0), s(ry_top), s(cx1), s(ry_top)], fill="#F0EBE0", width=s(0.7))

            fg, bg, code = STAMP_STYLE[stamp_kind]
            bw = 14.5
            brect = (cx1 - bw, cy - 6.2, cx1, cy + 6.2)
            rounded_rect(draw, brect, radius=2.6, fill=bg, outline=fg, width=0.7)
            draw_centered_text(draw, (brect[0] + brect[2]) / 2, cy, code, f_code, fg)

            src_w, _ = text_size(draw, src, f_src)
            src_x0 = brect[0] - 4.0 - src_w
            draw.text((sf(src_x0), sf(baseline)), src, font=f_src, fill=INK_MUTED, anchor="ls")

            num_txt = f"{num}."
            draw.text((sf(cx0), sf(baseline)), num_txt, font=f_num, fill=INK_MUTED, anchor="ls")
            lead_x = cx0 + 18.0
            lead_txt = f"{lead}:"
            draw.text((sf(lead_x), sf(baseline)), lead_txt, font=f_lead, fill=INK, anchor="ls")
            lw, _ = text_size(draw, lead_txt, f_lead)
            body_x = lead_x + lw + 3.2
            draw.text((sf(body_x), sf(baseline)), body, font=f_body, fill=INK_DARK, anchor="ls")
            bw_txt, _ = text_size(draw, body, f_body)

            assert body_x + bw_txt + 5.0 <= src_x0, (
                f"Wire row #{num} collides with source '{src}': right={body_x + bw_txt:.1f} vs src_x0={src_x0:.1f} ({lead}: {body})"
            )
            audit_boxes.append((f"wire:{num}", (cx0, ry_top + 1, cx1, ry_top + row_h - 1)))


# ---------- BAND 6: DATE CHECK AUDIT BOX + VERIFICATION LEGEND (y=938..1018) ----------

def draw_date_check_and_legend(
    draw: ImageDraw.ImageDraw,
    dc_rect: tuple[float, float, float, float],
    leg_rect: tuple[float, float, float, float],
    audit_boxes: list[tuple[str, tuple[float, float, float, float]]],
) -> None:
    x0, y0, x1, y1 = dc_rect
    rounded_rect(draw, dc_rect, radius=5.5, fill="#FFF8F6", outline="#DC2626", width=1.2)

    badge = (x0 + 6, y0 + 6, x0 + 96, y0 + 23)
    rounded_rect(draw, badge, radius=3.5, fill=CRIMSON)
    draw_centered_text(draw, (badge[0] + badge[2]) / 2, (badge[1] + badge[3]) / 2, "DATE CHECK", load_font(SANS_BLACK, 10.8), "#FFFFFF")

    f_b = load_font(SANS_BOLD, 11.4)
    f_r = load_font(SANS_SEMI, 11.2)
    l1 = "Left out on purpose — Sun 22 Nov or earlier: COP31 climate talks; Dymer Kyiv strike; Manchester Co-op Live 12k evac;"
    l2 = "Vegas F1; Alcaraz ATP; Liverpool 4–0; S. Korea exit; BepiColombo (21 Nov); EU €7.9B (20 Nov); Bank of Ghana (18 Nov); An-12 (17 Nov)."

    b1 = draw_left_text(draw, x0 + 104, y0 + 14.5, l1, f_b, INK)
    b2 = draw_left_text(draw, x0 + 8, y0 + 34.5, l2, f_r, INK_DARK)
    assert b1[2] <= x1 - 6 and b2[2] <= x1 - 6, f"Date-check clipped: {b1[2]:.1f}, {b2[2]:.1f}"
    audit_boxes.extend([("dc:1", b1), ("dc:2", b2)])

    lx0, ly0, lx1, ly1 = leg_rect
    cy = (ly0 + ly1) / 2
    cx = lx0 + 2
    f_l = load_font(SANS_BOLD, 9.8)
    for kind, desc in (
        ("CONFIRMED", "2+ outlets"),
        ("OFFICIAL", "agency/court"),
        ("REPORTED", "1 outlet"),
        ("CLAIM", "one side says"),
    ):
        fg, bg, _ = STAMP_STYLE[kind]
        tw, _ = text_size(draw, kind, load_font(SANS_BLACK, 8.6))
        pw = tw + 8.0
        rounded_rect(draw, (cx, cy - 6.5, cx + pw, cy + 6.5), radius=2.6, fill=bg, outline=fg, width=0.7)
        draw_centered_text(draw, cx + pw / 2, cy, kind, load_font(SANS_BLACK, 8.6), fg)
        cx += pw + 4.0
        tb = draw_left_text(draw, cx, cy, desc, f_l, INK_MUTED)
        cx = tb[2] + 10.0

    rb = draw_right_text(
        draw,
        lx1 - 2,
        cy,
        "Every story broke Mon 23 Nov 2026 (UTC) · Sources named with each item · Original vector drawings",
        load_font(SANS_BOLD, 9.8),
        INK_MUTED,
    )
    assert cx <= rb[0] - 6.0, f"Footer legend collision: left={cx:.1f} vs right={rb[0]:.1f}"


# ---------- LOSSLESS ADAPTIVE RGB PNG ENCODER ----------

def png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", crc)


def save_compact_rgb_png(img: Image.Image, path: Path) -> int:
    rgb = img.convert("RGB")
    arr = np.asarray(rgb, dtype=np.uint8)
    h, w, _ = arr.shape
    raw_rows = bytearray()
    prev = np.zeros((w, 3), dtype=np.int16)

    for y in range(h):
        cur = arr[y].astype(np.int16)
        left = np.zeros_like(cur)
        left[1:] = cur[:-1]
        up_left = np.zeros_like(cur)
        up_left[1:] = prev[:-1]

        c0 = cur & 0xFF
        c1 = (cur - left) & 0xFF
        c2 = (cur - prev) & 0xFF
        c3 = (cur - ((left + prev) >> 1)) & 0xFF

        p = left + prev - up_left
        pa = np.abs(p - left)
        pb = np.abs(p - prev)
        pc = np.abs(p - up_left)
        paeth = np.where((pa <= pb) & (pa <= pc), left, np.where(pb <= pc, prev, up_left))
        c4 = (cur - paeth) & 0xFF

        best_id = 0
        best_score = 1 << 60
        best_row = c0
        for fid, cand in ((0, c0), (1, c1), (2, c2), (3, c3), (4, c4)):
            signed = np.where(cand < 128, cand, 256 - cand)
            score = int(signed.sum())
            if score < best_score:
                best_score = score
                best_id = fid
                best_row = cand

        raw_rows.append(best_id)
        raw_rows.extend(best_row.astype(np.uint8).tobytes())
        prev = cur

    compressed = zlib.compress(bytes(raw_rows), level=9)
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    png_bytes = (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", ihdr)
        + png_chunk(b"IDAT", compressed)
        + png_chunk(b"IEND", b"")
    )
    path.write_bytes(png_bytes)
    return len(png_bytes)


# ---------- AUDIT ----------

def audit_layout(
    boxes: list[tuple[str, tuple[float, float, float, float]]],
    all_story_texts: list[str],
) -> None:
    issues: list[str] = []
    for txt in all_story_texts:
        low = txt.lower()
        for bad in BANNED_CARRYOVER_TOKENS:
            if bad in low:
                issues.append(f"BANNED carryover token '{bad}' in story: {txt}")

    for name, (x0, y0, x1, y1) in boxes:
        if x0 < 0 or y0 < 0 or x1 > WIDTH or y1 > HEIGHT:
            issues.append(f"Out of bounds {name}: {(x0, y0, x1, y1)}")

    for i in range(len(boxes)):
        n1, b1 = boxes[i]
        for j in range(i + 1, len(boxes)):
            n2, b2 = boxes[j]
            ix0 = max(b1[0], b2[0])
            iy0 = max(b1[1], b2[1])
            ix1 = min(b1[2], b2[2])
            iy1 = min(b1[3], b2[3])
            if ix1 - ix0 > 1.5 and iy1 - iy0 > 1.5:
                issues.append(f"Overlap between {n1} and {n2}: dx={ix1 - ix0:.1f}, dy={iy1 - iy0:.1f}")

    if issues:
        raise RuntimeError("Layout audit FAILED:\n" + "\n".join(issues))
    print(f"Layout audit: 0 issues ({len(boxes)} boxes checked, {len(all_story_texts)} stories date-clean)")


# ---------- MAIN RENDER ----------

def render() -> None:
    img = Image.new("RGB", (CW, CH), PAPER)
    draw = ImageDraw.Draw(img)
    audit_boxes: list[tuple[str, tuple[float, float, float, float]]] = []
    all_story_texts: list[str] = []

    # Band 1: Masthead (y=0..62px)
    draw_left_text(draw, 12, 11.5, "WORLD NEWS CHRONICLE  ·  ONE DAY IN ONE PICTURE", load_font(SANS_BLACK, 10.6), INK_MUTED)
    draw_right_text(draw, WIDTH - 12, 11.5, "36 STORIES  ·  7 REGIONS  ·  18 BEATS  ·  ALL SOURCED", load_font(SANS_BLACK, 10.6), CRIMSON)
    draw.line([s(12), s(20), s(WIDTH - 12), s(20)], fill=HAIRLINE, width=s(0.9))

    draw_centered_text(draw, WIDTH / 2, 40.0, "Monday 23 November 2026", load_font(SERIF_BOLD, 37.0), INK)
    draw.line([s(12), s(59.0), s(WIDTH - 12), s(59.0)], fill=INK, width=s(1.8))
    draw.line([s(12), s(61.5), s(WIDTH - 12), s(61.5)], fill=GOLD, width=s(1.0))

    # Band 2: THE DAY IN UTC Timeline (y=64..98px)
    draw_utc_timeline(draw, (12, 64, WIDTH - 12, 98), audit_boxes)

    # Band 3: Top 3 Flagship Lead Stories (y=102..330px, 3 cols x 326px)
    leads = [
        (
            1,
            "GLOBAL · MARKETS",
            "CONFIRMED",
            REGION_COLORS["ASIA"],
            "AI stock rout hits Asia; Korea & Taiwan act",
            "Kospi falls 3.3% and China hits 16-month lows on AI profit fears; Seoul readies $8B fund as Taiwan widens curbs.",
            "Reuters, AP",
            art_lead_asia,
        ),
        (
            2,
            "M. EAST · SECURITY",
            "CONFIRMED",
            REGION_COLORS["MIDDLE_EAST"],
            "Iran vows 'all tools' as Trump warns strikes",
            "Tehran answers U.S. Hormuz naval blockade warnings while Trump tells Fox strikes may resume after Jan 1.",
            "AFP, AA, Fox News",
            art_lead_iran,
        ),
        (
            3,
            "EUROPE · SPAIN LAW",
            "OFFICIAL",
            REGION_COLORS["EUROPE"],
            "Spain Supreme Court grants Puigdemont amnesty",
            "Criminal Chamber closes 2017 Catalan independence proceedings against exiled ex-leader Carles Puigdemont and two aides.",
            "Supreme Court, Reuters",
            art_lead_spain,
        ),
    ]
    lw = 326.0
    lgap = 11.0
    for idx, (num, kicker, stamp, col, head, deck, src, art_fn) in enumerate(leads):
        lx0 = 12.0 + idx * (lw + lgap)
        draw_lead_card(draw, (lx0, 102, lx0 + lw, 330), num, kicker, stamp, col, head, deck, src, art_fn, audit_boxes)
        all_story_texts.append(f"{head} {deck}")

    # Band 4: 10 Illustrated Feature Cards (y=336..676px, 2 rows x 5 cols, 194x167px)
    features = [
        (4, "CRICKET · NZ", "OFFICIAL", REGION_COLORS["OCEANIA"], "New Zealand hold India to Test draw", "Hosts bat out day 5 in Wellington after India's 720/9d to draw.", "ICC, ESPN", art_f_cricket),
        (5, "EUROPE GAS", "CONFIRMED", REGION_COLORS["EUROPE"], "European gas jumps 6% to €93/MWh", "Cold winter forecasts and Hormuz risks push Dutch TTF higher.", "FT, MUFG", art_f_gas),
        (6, "BELGIUM", "CONFIRMED", REGION_COLORS["EUROPE"], "National strike grounds Belgian skies", "Walkout halts Belgian ATC 07:00–21:00 local (06–20 UTC).", "AA, Al Jazeera", art_f_belgium),
        (7, "GERMANY", "CONFIRMED", REGION_COLORS["EUROPE"], "450 German schools & Danish bomb hoaxes", "Police deem emailed threats to schools & Danish sites unfounded.", "Police, DPA", art_f_schools),
        (8, "LIBYA OIL", "CONFIRMED", REGION_COLORS["AFRICA"], "Libya Sharara shut cuts 350k bpd oil", "Unauthorized valve closure halts major southwestern crude field.", "NOC, AA, Reuters", art_f_libya),
        (9, "AFRICA HEALTH", "OFFICIAL", REGION_COLORS["AFRICA"], "Africa Health Summit opens in Addis", "CPHIA launches maternal plan & eyes 60% local vaccines by 2040.", "Africa CDC", art_f_cphia),
        (10, "US WEATHER", "CONFIRMED", REGION_COLORS["AMERICAS"], "Bay Area braces for storms & king tides", "Forecast +2.8ft surge prompts flood barriers at SFO.", "CNN, SFO", art_f_tides),
        (11, "GUIANA SPACE", "OFFICIAL", REGION_COLORS["S_AMERICA"], "Ariane 6 VA271 halted in Kourou", "Ground-support fault pauses launch of 36 Amazon Leo satellites.", "Arianespace, CNES", art_f_ariane),
        (12, "MEDICINE", "OFFICIAL", REGION_COLORS["GLOBAL"], "Novartis heart trial meets goal", "Phase III ORION-4 readout shows Leqvio cut major cardiac events.", "Novartis", art_f_heart),
        (13, "OCEANIA", "OFFICIAL", REGION_COLORS["OCEANIA"], "USGS logs M6.5 quake in Vanuatu", "Strong deep tremor shakes South Pacific; no tsunami alert issued.", "USGS", art_f_quake),
    ]
    fw, fh = 194.0, 167.0
    fgap_x, fgap_y = 7.5, 6.0
    for idx, (num, kicker, stamp, col, head, deck, src, art_fn) in enumerate(features):
        r, c = divmod(idx, 5)
        fx0 = 12.0 + c * (fw + fgap_x)
        fy0 = 336.0 + r * (fh + fgap_y)
        draw_feature_card(draw, (fx0, fy0, fx0 + fw, fy0 + fh), num, kicker, stamp, col, head, deck, src, art_fn, audit_boxes)
        all_story_texts.append(f"{head} {deck}")

    # Band 5: Compact Natural Earth Map (Left) + 23-Story Light-Ivory Wire (Right)
    draw_compact_map(draw, (12, 682, 290, 934), audit_boxes)

    left_wire = [
        (14, "US Economy", "Bessent warns hawkish Fed risks growth", "AP", "OFFICIAL"),
        (15, "Canada", "Bombardier union votes 97.8% for strike", "AVI-GO", "OFFICIAL"),
        (16, "Colombia", "NGO warns Chocó malaria surged 46%", "STC", "REPORTED"),
        (17, "Falklands", "Groups warn oil plan threatens sea life", "Guardian", "REPORTED"),
        (18, "UK Markets", "Compass Group plans NY primary listing", "LSE", "OFFICIAL"),
        (19, "UK Police", "Met opens criminal probe of D. Walliams", "ITV/CNN", "CONFIRMED"),
        (20, "UK Media", "Report warns BBC fee below 50% homes", "Guardian", "REPORTED"),
        (21, "UK–EU", "Youth-mobility deal hinges on tuition", "Guardian", "REPORTED"),
        (22, "Europe", "Living-cost rallies hit EU capitals", "Al Jazeera", "REPORTED"),
        (23, "Japan", "Education Min. Seki faces exit pressure", "Xinhua", "REPORTED"),
        (24, "Singapore", "MAS & PBOC widen offshore RMB hub", "MAS", "OFFICIAL"),
        (25, "India–Nepal", "Leaders sign hydro & rail pacts", "Hindu", "OFFICIAL"),
    ]
    right_wire = [
        (26, "S. Korea", "New FM Lim discusses Qatar LNG supply", "K.Herald", "OFFICIAL"),
        (27, "APAC Deals", "Macquarie agrees $1.2B tower buyout", "Reuters", "OFFICIAL"),
        (28, "Science", "Cambridge traces blood cancer to early cells", "Nature", "OFFICIAL"),
        (29, "Gaza Aid", "Oxfam warns 99% faces toxic risk", "Oxfam", "REPORTED"),
        (30, "Gulf Oil", "Saudi & Japan add 16M bbl crude reserve", "MUFG", "REPORTED"),
        (31, "Hormuz", "Monitors say Gulf ship attacks hit high", "JPost", "REPORTED"),
        (32, "Africa Water", "Mashatile opens Durban water summit", "SABC", "OFFICIAL"),
        (33, "Ivory Coast", "Germany's Steinmeier opens Africa tour", "DPA", "OFFICIAL"),
        (34, "Southern Africa", "S. Africa & Zambia link customs", "SARS", "OFFICIAL"),
        (35, "Australia", "Chalmers sees <2% GDP, no recession", "Guardian", "OFFICIAL"),
        (36, "Oil Markets", "Brent steadies near $91.97 amid Gulf risk", "Reuters", "REPORTED"),
    ]
    for grp in (left_wire, right_wire):
        for num, lead, body, src, _ in grp:
            all_story_texts.append(f"{lead}: {body} ({src})")

    draw_ivory_wire(draw, (298, 682, WIDTH - 12, 934), left_wire, right_wire, audit_boxes)

    # Band 6: DATE CHECK Box + Verification Legend (y=938..1018px)
    draw_date_check_and_legend(draw, (12, 938, WIDTH - 12, 988), (12, 992, WIDTH - 12, 1018), audit_boxes)

    assert len(all_story_texts) == 36, f"Expected 36 stories, got {len(all_story_texts)}"
    audit_layout(audit_boxes, all_story_texts)

    # Downsample 2x -> 1x with LANCZOS (archival print sharpness)
    final_img = img.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    nbytes = save_compact_rgb_png(final_img, OUT_PNG)
    print(f"Rendered {OUT_PNG}: {WIDTH}x{HEIGHT} RGB PNG, {nbytes:,} bytes ({nbytes / 1024:.1f} KiB)")
    assert nbytes < 1_048_576, f"PNG exceeds 1 MiB: {nbytes}"


if __name__ == "__main__":
    render()
