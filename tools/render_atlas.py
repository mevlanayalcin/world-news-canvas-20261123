#!/usr/bin/env python3
"""Render the 1024x1024 Illustrated World News Atlas (v6 Hybrid, 25 sourced stories) for Monday 23 November 2026.

Championship Hybrid Museum Architecture with strict MIN_FONT_PX = 15.0 everywhere:
- Top Masthead (y=0..76): 15px gold ledger ribbon + 44px broadsheet serif date
- Hero Visual Band (y=79..331): Airy Natural Earth 110m World Map (8 crisp >=15px dark-navy callouts,
  zero anonymous dots, exact single-city pins) + 2 Giant Illustrated Hero Leads (20px serif + 15px sources)
- 3x3 Giant Panoramic Museum Gallery (y=337..787): 9 large (328x146px) bespoke illustrated cards
  with 15px region/beat headers, 15px right-aligned outlet sources, panoramic vector art, and 18.5px serif headlines
  (= 11 full illustrated visual stories across all 7 regions, including EU €7.9B Ukraine & Novartis ORION-4!)
- Bottom Dark-Navy Attributed Wire (y=793..983): 2x7 = 14 single-line 15px bold white dispatches with
  15px right-aligned gold source tags (= 25 total verified, attributed Monday 23 Nov stories!)
- Bottom DATE CHECK Bar (y=987..1019): Crisp 15px high-contrast exclusion bar naming prior-day 21-22 Nov items
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
MIN_FONT_PX = 15.0

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_PNG = REPO_ROOT / "entry.png"
GEOJSON_PATH = Path("/tmp/ne_110m_land.geojson")

# Open system fonts
SERIF_BOLD = "/usr/share/fonts/truetype/noto/NotoSerif-Bold.ttf"
SANS_BLACK = "/usr/share/fonts/truetype/lato/Lato-Black.ttf"
SANS_BOLD = "/usr/share/fonts/truetype/lato/Lato-Bold.ttf"
SANS_SEMI = "/usr/share/fonts/truetype/lato/Lato-Semibold.ttf"

# Warm Archival Broadsheet Palette
PAPER = "#FAF6EE"
CARD_BG = "#FFFFFF"
HAIRLINE = "#D6CCBA"
INK = "#0F172A"
INK_MUTED = "#334155"
NAVY_DARK = "#0D1B2A"
NAVY_MID = "#162A40"
GOLD = "#C89B3C"
GOLD_LIGHT = "#F5D78E"

OCEAN = "#DCEAF6"
OCEAN_GRID = "#C7DCEE"
LAND_FILL = "#EFE5CF"
LAND_STROKE = "#8D7F68"

REGION_COLORS = {
    "GLOBAL": "#B91C1C",
    "MIDDLE_EAST": "#C2410C",
    "EUROPE": "#1D4ED8",
    "AFRICA": "#047857",
    "AMERICAS": "#3730A3",
    "ASIA": "#9D174D",
    "S_AMERICA": "#0F766E",
    "OCEANIA": "#92400E",
    "SCIENCE": "#0E7490",
}

BANNED_CARRYOVER_TOKENS = (
    "merkury",
    "verica",
    "verstappen",
    "alcaraz",
    "liverpool",
    "bepicolombo",
    "cop31",
)


def s(v: float) -> int:
    return int(round(v * SCALE))


def sf(v: float) -> float:
    return v * SCALE


def load_font(path: str, size_px: float) -> ImageFont.FreeTypeFont:
    assert size_px >= MIN_FONT_PX, f"Font size {size_px}px violates strict MIN_FONT_PX={MIN_FONT_PX}!"
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
    return (
        (x + box[0]) / SCALE,
        (y + box[1]) / SCALE,
        (x + box[2]) / SCALE,
        (y + box[3]) / SCALE,
    )


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
    return (
        (x + box[0]) / SCALE,
        (y + box[1]) / SCALE,
        (x + box[2]) / SCALE,
        (y + box[3]) / SCALE,
    )


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
    return (
        (x + box[0]) / SCALE,
        (y + box[1]) / SCALE,
        (x + box[2]) / SCALE,
        (y + box[3]) / SCALE,
    )


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


def top_rounded_strip(
    draw: ImageDraw.ImageDraw,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    radius: float,
    fill: str,
) -> None:
    draw.rounded_rectangle([s(x0), s(y0), s(x1), s(y1)], radius=s(radius), fill=fill)
    draw.rectangle([s(x0), s(y1 - radius), s(x1), s(y1)], fill=fill)


def draw_plaque(
    draw: ImageDraw.ImageDraw,
    x1: float,
    y0: float,
    text: str,
    bg: str,
    fg: str = "#FFFFFF",
    font_px: float = 15.0,
    pad_x: float = 6.0,
    h: float = 21.0,
) -> None:
    f = load_font(SANS_BLACK, font_px)
    tw, _ = text_size(draw, text, f)
    w = tw + pad_x * 2
    rect = (x1 - w, y0, x1, y0 + h)
    rounded_rect(draw, (rect[0] - 1.2, rect[1] - 1.2, rect[2] + 1.2, rect[3] + 1.2), radius=5.0, fill="#FFFFFF")
    rounded_rect(draw, rect, radius=4.0, fill=bg)
    draw_centered_text(draw, (rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2, text, f, fg)


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


# ---------- AIRY LABELED NATURAL EARTH WORLD MAP (556 x 252px) ----------

def draw_world_map(
    draw: ImageDraw.ImageDraw,
    panel: tuple[float, float, float, float],
    audit_boxes: list[tuple[str, tuple[float, float, float, float]]],
) -> None:
    px0, py0, px1, py1 = panel
    footer_h = 26.0
    map_box = (px0, py0, px1, py1 - footer_h)
    mx0, my0, mx1, my1 = map_box

    rounded_rect(draw, panel, radius=7, fill=OCEAN, outline=HAIRLINE, width=1.1)

    for lon in range(-150, 180, 45):
        gx, _ = project_lonlat(lon, 0, map_box)
        if mx0 + 4 < gx < mx1 - 4:
            draw.line([s(gx), s(my0 + 2), s(gx), s(my1)], fill=OCEAN_GRID, width=1)
    for lat in (-30, 0, 30, 60):
        _, gy = project_lonlat(0, lat, map_box)
        if my0 + 4 < gy < my1 - 4:
            draw.line([s(mx0 + 2), s(gy), s(mx1 - 2), s(gy)], fill=OCEAN_GRID, width=1)

    if GEOJSON_PATH.exists():
        geo = json.loads(GEOJSON_PATH.read_text(encoding="utf-8"))
        for feat in geo.get("features", []):
            geom = feat.get("geometry", {})
            gtype = geom.get("type")
            coords = geom.get("coordinates", [])
            polys = [coords] if gtype == "Polygon" else (coords if gtype == "MultiPolygon" else [])
            for poly in polys:
                if not poly:
                    continue
                ring = poly[0]
                pts: list[tuple[int, int]] = []
                for lon, lat in ring:
                    if lat < -54.0:
                        continue
                    clon = max(-160.0, min(180.0, lon))
                    clat = max(-54.0, min(75.0, lat))
                    x, y = project_lonlat(clon, clat, map_box)
                    pts.append((s(x), s(y)))
                if len(pts) >= 3:
                    draw.polygon(pts, fill=LAND_FILL, outline=LAND_STROKE)

    # 8 high-contrast >=15px dark-navy callout pills (0 anonymous dots, 1 exact city per pin!)
    callouts = [
        ("U.S. Fed", -77.0, 38.9, mx0 + 58, my0 + 82, REGION_COLORS["AMERICAS"]),
        ("Ariane 6", -52.7, 5.2, mx0 + 96, my0 + 186, REGION_COLORS["S_AMERICA"]),
        ("EU Gas €93", 4.9, 52.3, mx0 + 236, my0 + 20, REGION_COLORS["EUROPE"]),
        ("Ukraine €7.9B", 30.5, 50.4, mx0 + 368, my0 + 20, REGION_COLORS["EUROPE"]),
        ("Libya Oil", 12.2, 26.5, mx0 + 228, my0 + 138, REGION_COLORS["AFRICA"]),
        ("Addis Health", 38.7, 9.0, mx0 + 320, my0 + 190, REGION_COLORS["AFRICA"]),
        ("Iran Oil", 56.3, 26.5, mx0 + 386, my0 + 114, REGION_COLORS["MIDDLE_EAST"]),
        ("Asia AI Rout", 126.9, 37.5, mx0 + 478, my0 + 42, REGION_COLORS["GLOBAL"]),
        ("NZ Draw", 174.8, -41.3, mx0 + 474, my0 + 190, REGION_COLORS["OCEANIA"]),
    ]
    pill_font = load_font(SANS_BLACK, 15.0)
    for label, lon, lat, lx, ly, col in callouts:
        px, py = project_lonlat(lon, lat, map_box)
        tw, _ = text_size(draw, label, pill_font)
        pw = tw + 18.0
        ph = 23.0
        prect = (lx - pw / 2, ly - ph / 2, lx + pw / 2, ly + ph / 2)
        assert prect[0] >= mx0 + 3 and prect[2] <= mx1 - 3, f"Map pill X clipped: {label} ({prect})"
        assert prect[1] >= my0 + 3 and prect[3] <= my1 - 3, f"Map pill Y clipped: {label} ({prect})"
        # Crisp white-outlined leader line
        draw.line([s(px), s(py), s(lx), s(ly)], fill="#FFFFFF", width=s(2.8))
        draw.line([s(px), s(py), s(lx), s(ly)], fill=NAVY_DARK, width=s(1.4))
        # Exact target pin
        draw.ellipse([s(px - 5.2), s(py - 5.2), s(px + 5.2), s(py + 5.2)], fill=col, outline="#FFFFFF", width=s(1.8))
        # High-contrast dark-navy pill with colored left accent bar
        rounded_rect(draw, (prect[0] - 1.2, prect[1] - 1.2, prect[2] + 1.2, prect[3] + 1.2), radius=5.2, fill="#FFFFFF")
        rounded_rect(draw, prect, radius=4.2, fill=NAVY_DARK)
        rounded_rect(draw, (prect[0], prect[1], prect[0] + 5.5, prect[3]), radius=2.5, fill=col)
        draw_left_text(draw, prect[0] + 10.0, ly, label, pill_font, "#FFFFFF")
        audit_boxes.append((f"map:{label}", prect))

    # Clean bottom map ribbon (15px bold)
    ly0 = py1 - footer_h
    rounded_rect(draw, (px0 + 1, ly0, px1 - 1, py1 - 1), radius=6, fill="#F5EFE3")
    draw.rectangle([s(px0 + 1), s(ly0), s(px1 - 1), s(ly0 + 8)], fill="#F5EFE3")
    draw.line([s(px0 + 1), s(ly0), s(px1 - 1), s(ly0)], fill=HAIRLINE, width=s(1.0))
    draw_centered_text(
        draw,
        (px0 + px1) / 2,
        ly0 + footer_h / 2,
        "7 REGIONS · 17 BEATS · ALL 25 STORIES ATTRIBUTED",
        load_font(SANS_BLACK, 15.0),
        INK,
    )


# ---------- 2 HERO ILLUSTRATIONS (116 x 86px) ----------

def art_hero_asia(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float]) -> None:
    x0, y0, x1, y1 = box
    rounded_rect(draw, box, radius=5, fill="#FEF2F2", outline="#FECACA", width=1.1)
    draw.rectangle([s(x0 + 2), s(y1 - 28), s(x1 - 2), s(y1 - 2)], fill="#FDE8E8")
    for tx, th, tw in [(x0 + 6, 22, 12), (x0 + 21, 32, 11), (x0 + 35, 38, 12), (x0 + 50, 26, 13)]:
        draw.rectangle([s(tx), s(y1 - 2 - th), s(tx + tw), s(y1 - 2)], fill="#E2B8B8")
    for bx, by, bw, bh, col in [(x0 + 10, y0 + 10, 8, 15, "#DC2626"), (x0 + 24, y0 + 20, 8, 17, "#DC2626"), (x0 + 38, y0 + 31, 8, 19, "#B91C1C"), (x0 + 52, y0 + 42, 8, 20, "#991B1B")]:
        draw.rectangle([s(bx), s(by), s(bx + bw), s(by + bh)], fill=col)
    draw.line([(s(x0 + 8), s(y0 + 12)), (s(x0 + 36), s(y0 + 31)), (s(x0 + 47), s(y0 + 26)), (s(x0 + 66), s(y0 + 62))], fill="#7F1D1D", width=s(3.4))
    scx, scy = x1 - 22, y1 - 22
    shield = [(s(scx), s(scy - 16)), (s(scx + 14), s(scy - 11)), (s(scx + 12), s(scy + 4)), (s(scx), s(scy + 16)), (s(scx - 12), s(scy + 4)), (s(scx - 14), s(scy - 11))]
    draw.polygon(shield, fill=NAVY_DARK)
    draw.line(shield + [shield[0]], fill=GOLD, width=s(2.0))
    draw.line([(s(scx - 5.5), s(scy + 1)), (s(scx - 1), s(scy + 5.5)), (s(scx + 6.5), s(scy - 4.5))], fill="#FACC15", width=s(2.8))
    draw_plaque(draw, x1 - 4, y0 + 4, "-10%", "#B91C1C")


def art_hero_iran(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float]) -> None:
    x0, y0, x1, y1 = box
    h = y1 - y0
    rounded_rect(draw, box, radius=5, fill="#FFF4E6", outline="#FED7AA", width=1.1)
    draw.ellipse([s(x0 + 6), s(y0 + 6), s(x0 + 22), s(y0 + 22)], fill="#FB923C")
    sea_y = y0 + h * 0.58
    rounded_rect(draw, (x0 + 1, sea_y, x1 - 1, y1 - 1), radius=4, fill="#1E3A5F")
    draw.rectangle([s(x0 + 1), s(sea_y), s(x1 - 1), s(sea_y + 8)], fill="#1E3A5F")
    for wy, wx0, wx1 in [(sea_y + 10, x0 + 10, x0 + 48), (sea_y + 20, x0 + 50, x0 + 102)]:
        draw.line([s(wx0), s(wy), s(wx1), s(wy)], fill="#60A5FA", width=s(2.0))
    hull = [(s(x0 + 9), s(sea_y + 4)), (s(x0 + 68), s(sea_y + 4)), (s(x0 + 76), s(sea_y - 9)), (s(x0 + 12), s(sea_y - 9))]
    draw.polygon(hull, fill="#0F172A")
    draw.rectangle([s(x0 + 13), s(sea_y - 13), s(x0 + 68), s(sea_y - 8)], fill="#DC2626")
    draw.rectangle([s(x0 + 17), s(sea_y - 24), s(x0 + 31), s(sea_y - 13)], fill="#F8FAFC", outline="#0F172A", width=s(1.2))
    bcx, bcy = x1 - 21, sea_y - 10
    draw.arc([s(bcx - 16), s(bcy - 16), s(bcx + 16), s(bcy + 16)], start=110, end=250, fill="#DC2626", width=s(3.4))
    draw.ellipse([s(bcx - 11), s(bcy - 11), s(bcx + 11), s(bcy + 11)], fill="#DC2626", outline="#FFFFFF", width=s(1.8))
    draw.rectangle([s(bcx - 5.5), s(bcy - 2.2), s(bcx + 5.5), s(bcy + 2.2)], fill="#FFFFFF")


# ---------- 9 WIDE PANORAMIC MUSEUM ILLUSTRATIONS (316 x 60px) ----------

def art_pan_ukraine(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float]) -> None:
    x0, y0, x1, y1 = box
    rounded_rect(draw, box, radius=5, fill="#EFF6FF", outline="#BFDBFE", width=1.0)
    # Ukrainian sky/wheat shield left-center
    cx, cy = x0 + 48, (y0 + y1) / 2 + 1
    shield = [(s(cx), s(cy - 22)), (s(cx + 21), s(cy - 15)), (s(cx + 18), s(cy + 7)), (s(cx), s(cy + 22)), (s(cx - 18), s(cy + 7)), (s(cx - 21), s(cy - 15))]
    draw.polygon(shield, fill="#1D4ED8")
    lower = [(s(cx + 19), s(cy)), (s(cx + 18), s(cy + 7)), (s(cx), s(cy + 22)), (s(cx - 18), s(cy + 7)), (s(cx - 19), s(cy))]
    draw.polygon(lower, fill="#FACC15")
    draw.line(shield + [shield[0]], fill="#1E3A8A", width=s(2.0))
    # EU golden stars arc
    for i in range(7):
        sx = x0 + 92 + i * 16
        sy = y0 + 18 + (i % 2) * 5
        draw.ellipse([s(sx - 3.2), s(sy - 3.2), s(sx + 3.2), s(sy + 3.2)], fill="#F59E0B")
    # Rising euro funding bars
    for i, bh in enumerate((18, 28, 38, 46)):
        bx = x0 + 100 + i * 26
        rounded_rect(draw, (bx, y1 - 6 - bh, bx + 18, y1 - 6), radius=3, fill="#2563EB" if i < 3 else "#1E40AF")
        draw.ellipse([s(bx), s(y1 - 9 - bh), s(bx + 18), s(y1 - 3 - bh)], fill="#FACC15")
    draw_plaque(draw, x1 - 6, y0 + 5, "€7.9B", "#1D4ED8")


def art_pan_gas(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float]) -> None:
    x0, y0, x1, y1 = box
    mid = x0 + 112
    rounded_rect(draw, box, radius=5, fill="#FEF3C7", outline="#FDE68A", width=1.0)
    draw.rectangle([s(x0 + 1), s(y0 + 1), s(mid), s(y1 - 1)], fill="#DBEAFE")
    # Cold snap snowflake + European roofs
    cx, cy, r = x0 + 32, y0 + 28, 14.0
    for deg in range(0, 360, 60):
        rad = math.radians(deg)
        draw.line([s(cx), s(cy), s(cx + math.cos(rad) * r), s(cy + math.sin(rad) * r)], fill="#1D4ED8", width=s(2.4))
    for rx, rh, rw in [(x0 + 56, 22, 20), (x0 + 80, 30, 22)]:
        draw.rectangle([s(rx), s(y1 - 2 - rh), s(rx + rw), s(y1 - 2)], fill="#60A5FA")
        draw.polygon([(s(rx - 2), s(y1 - 2 - rh)), (s(rx + rw / 2), s(y1 - 11 - rh)), (s(rx + rw + 2), s(y1 - 2 - rh))], fill="#1E40AF")
    # Natural gas flame + price surge line
    fx, fy = mid + 34, y1 - 5
    draw.polygon([(s(fx), s(y0 + 7)), (s(fx + 16), s(y0 + 30)), (s(fx + 13), s(fy)), (s(fx - 13), s(fy)), (s(fx - 16), s(y0 + 30))], fill="#EA580C")
    draw.polygon([(s(fx), s(y0 + 21)), (s(fx + 8), s(y0 + 38)), (s(fx + 7), s(fy)), (s(fx - 7), s(fy)), (s(fx - 8), s(y0 + 38))], fill="#FACC15")
    draw.line([(s(mid + 64), s(y1 - 12)), (s(mid + 92), s(y1 - 22)), (s(mid + 114), s(y0 + 26)), (s(x1 - 78), s(y0 + 12))], fill="#DC2626", width=s(3.5))
    draw_plaque(draw, x1 - 6, y0 + 5, "+6% €93", "#1D4ED8")


def art_pan_libya(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float]) -> None:
    x0, y0, x1, y1 = box
    rounded_rect(draw, box, radius=5, fill="#FEF3C7", outline="#FDE68A", width=1.0)
    # Desert dunes
    draw.polygon([(s(x0 + 1), s(y1 - 1)), (s(x0 + 1), s(y1 - 16)), (s(x0 + 100), s(y1 - 26)), (s(x0 + 220), s(y1 - 14)), (s(x1 - 1), s(y1 - 22)), (s(x1 - 1), s(y1 - 1))], fill="#E5C992")
    # Heavy pipeline + shut red wheel valve + crude oil drop
    py = (y0 + y1) / 2
    draw.rectangle([s(x0 + 8), s(py - 6), s(x1 - 92), s(py + 6)], fill="#475569", outline="#1E293B", width=s(1.4))
    draw.rectangle([s(x1 - 98), s(py - 9), s(x1 - 88), s(py + 9)], fill="#334155")
    vcx, vcy = x0 + 98, py
    draw.ellipse([s(vcx - 20), s(vcy - 20), s(vcx + 20), s(vcy + 20)], fill="#FFFFFF", outline="#DC2626", width=s(4.0))
    for deg in (0, 60, 120):
        rad = math.radians(deg)
        draw.line([s(vcx - math.cos(rad) * 16), s(vcy - math.sin(rad) * 16), s(vcx + math.cos(rad) * 16), s(vcy + math.sin(rad) * 16)], fill="#DC2626", width=s(2.6))
    draw.ellipse([s(vcx - 5), s(vcy - 5), s(vcx + 5), s(vcy + 5)], fill="#991B1B")
    dx, dy = x1 - 74, py + 12
    draw.polygon([(s(dx), s(dy - 12)), (s(dx + 8), s(dy + 2)), (s(dx), s(dy + 10)), (s(dx - 8), s(dy + 2))], fill="#0F172A")
    draw_plaque(draw, x1 - 6, y0 + 5, "-350K", "#047857")


def art_pan_fed(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float]) -> None:
    x0, y0, x1, y1 = box
    rounded_rect(draw, box, radius=5, fill="#EEF2FF", outline="#C7D2FE", width=1.0)
    # Neoclassical Federal Reserve facade
    base_y = y1 - 8
    draw.rectangle([s(x0 + 18), s(base_y), s(x0 + 122), s(base_y + 5)], fill="#312E81")
    draw.polygon([(s(x0 + 16), s(y0 + 24)), (s(x0 + 70), s(y0 + 6)), (s(x0 + 124), s(y0 + 24))], fill="#3730A3")
    draw.rectangle([s(x0 + 20), s(y0 + 24), s(x0 + 120), s(y0 + 28)], fill="#4338CA")
    for cx in (x0 + 28, x0 + 48, x0 + 68, x0 + 88, x0 + 108):
        draw.rectangle([s(cx - 4), s(y0 + 28), s(cx + 4), s(base_y)], fill="#818CF8", outline="#3730A3", width=s(1.0))
    # Bold amber warning triangle
    tx, ty = x0 + 178, (y0 + y1) / 2 + 2
    tri = [(s(tx), s(ty - 21)), (s(tx + 22), s(ty + 17)), (s(tx - 22), s(ty + 17))]
    draw.polygon(tri, fill="#F59E0B")
    draw.line(tri + [tri[0]], fill="#92400E", width=s(2.4))
    draw.rectangle([s(tx - 2.5), s(ty - 8), s(tx + 2.5), s(ty + 4)], fill="#0F172A")
    draw.ellipse([s(tx - 2.6), s(ty + 7.5), s(tx + 2.6), s(ty + 12.7)], fill="#0F172A")
    draw_plaque(draw, x1 - 6, y0 + 5, "FED", "#3730A3")


def art_pan_rmb(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float]) -> None:
    x0, y0, x1, y1 = box
    rounded_rect(draw, box, radius=5, fill="#FDF2F8", outline="#FBCFE8", width=1.0)
    cy = (y0 + y1) / 2
    c1x, c2x = x0 + 66, x0 + 188
    draw.line([s(c1x + 22), s(cy - 9), s(c2x - 22), s(cy - 9)], fill="#9D174D", width=s(3.2))
    draw.polygon([(s(c2x - 22), s(cy - 15)), (s(c2x - 12), s(cy - 9)), (s(c2x - 22), s(cy - 3))], fill="#9D174D")
    draw.line([s(c2x - 22), s(cy + 9), s(c1x + 22), s(cy + 9)], fill="#0F766E", width=s(3.2))
    draw.polygon([(s(c1x + 22), s(cy + 3)), (s(c1x + 12), s(cy + 9)), (s(c1x + 22), s(cy + 15))], fill="#0F766E")
    r = 22.0
    draw.ellipse([s(c1x - r), s(cy - r), s(c1x + r), s(cy + r)], fill="#9D174D", outline="#FFFFFF", width=s(2.0))
    draw_centered_text(draw, c1x, cy, "¥", load_font(SANS_BLACK, 24.0), "#FDE68A")
    draw.ellipse([s(c2x - r), s(cy - r), s(c2x + r), s(cy + r)], fill="#0F766E", outline="#FFFFFF", width=s(2.0))
    draw_centered_text(draw, c2x, cy, "S$", load_font(SANS_BLACK, 19.0), "#FFFFFF")
    draw_plaque(draw, x1 - 6, y0 + 5, "RMB", "#9D174D")


def art_pan_ariane(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float]) -> None:
    x0, y0, x1, y1 = box
    rounded_rect(draw, box, radius=5, fill="#F0FDFA", outline="#99F6E4", width=1.0)
    # Contained orbital arc + pad
    draw.arc([s(x0 + 16), s(y0 + 10), s(x1 - 76), s(y1 + 56)], start=205, end=330, fill="#5EEAD4", width=s(2.2))
    draw.rectangle([s(x0 + 18), s(y1 - 9), s(x0 + 156), s(y1 - 3)], fill="#334155")
    # Gantry + sleek Ariane 6 rocket
    draw.rectangle([s(x0 + 36), s(y0 + 12), s(x0 + 46), s(y1 - 9)], fill="#64748B")
    draw.line([s(x0 + 46), s(y0 + 25), s(x0 + 76), s(y0 + 25)], fill="#475569", width=s(2.4))
    rx = x0 + 88
    draw.polygon([(s(rx), s(y0 + 5)), (s(rx + 9), s(y0 + 19)), (s(rx - 9), s(y0 + 19))], fill="#0F766E")
    draw.rectangle([s(rx - 9), s(y0 + 19), s(rx + 9), s(y1 - 11)], fill="#FFFFFF", outline="#0F172A", width=s(1.4))
    draw.rectangle([s(rx - 16), s(y0 + 31), s(rx - 9), s(y1 - 10)], fill="#0D9488")
    draw.rectangle([s(rx + 9), s(y0 + 31), s(rx + 16), s(y1 - 10)], fill="#0D9488")
    # Red HOLD pause emblem
    hx, hy = x0 + 188, (y0 + y1) / 2
    draw.ellipse([s(hx - 18), s(hy - 18), s(hx + 18), s(hy + 18)], fill="#DC2626", outline="#FFFFFF", width=s(2.2))
    draw.rectangle([s(hx - 6.5), s(hy - 9), s(hx - 2), s(hy + 9)], fill="#FFFFFF")
    draw.rectangle([s(hx + 2), s(hy - 9), s(hx + 6.5), s(hy + 9)], fill="#FFFFFF")
    draw_plaque(draw, x1 - 6, y0 + 5, "HOLD", "#0F766E")


def art_pan_cphia(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float]) -> None:
    x0, y0, x1, y1 = box
    rounded_rect(draw, box, radius=5, fill="#ECFDF5", outline="#A7F3D0", width=1.0)
    cy = (y0 + y1) / 2
    # Medical cross shield
    cx = x0 + 56
    draw.ellipse([s(cx - 22), s(cy - 22), s(cx + 22), s(cy + 22)], fill="#047857", outline="#065F46", width=s(2.0))
    draw.rectangle([s(cx - 5.5), s(cy - 14), s(cx + 5.5), s(cy + 14)], fill="#FFFFFF")
    draw.rectangle([s(cx - 14), s(cy - 5.5), s(cx + 14), s(cy + 5.5)], fill="#FFFFFF")
    # 3 vaccine vials (manufacturing scale-up)
    for i in range(3):
        vx0 = x0 + 106 + i * 32
        vy0, vy1 = y0 + 12, y1 - 7
        rounded_rect(draw, (vx0, vy0 + 7, vx0 + 22, vy1), radius=4, fill="#FFFFFF", outline="#047857", width=s(1.8))
        draw.rectangle([s(vx0 + 2), s(vy0 + 20), s(vx0 + 20), s(vy1 - 2)], fill="#34D399")
        draw.rectangle([s(vx0 + 4), s(vy0), s(vx0 + 18), s(vy0 + 7)], fill="#065F46")
    draw_plaque(draw, x1 - 6, y0 + 5, "60%", "#047857")


def art_pan_heart(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float]) -> None:
    x0, y0, x1, y1 = box
    rounded_rect(draw, box, radius=5, fill="#ECFEFF", outline="#A5F3FC", width=1.0)
    mx0, my0, mx1, my1 = x0 + 12, y0 + 6, x1 - 92, y1 - 6
    rounded_rect(draw, (mx0, my0, mx1, my1), radius=6, fill="#0F172A", outline="#0E7490", width=s(1.8))
    ey = (my0 + my1) / 2 + 2
    pts = [
        (mx0 + 10, ey), (mx0 + 42, ey), (mx0 + 52, ey - 8), (mx0 + 60, ey + 7),
        (mx0 + 72, ey - 20), (mx0 + 84, ey + 15), (mx0 + 96, ey - 5), (mx0 + 112, ey),
        (mx0 + 150, ey), (mx1 - 12, ey),
    ]
    draw.line([(s(px), s(py)) for px, py in pts], fill="#22D3EE", width=s(2.8))
    hx, hy = mx1 - 28, my0 + 20
    draw.ellipse([s(hx - 10), s(hy - 8), s(hx + 1), s(hy + 3)], fill="#EF4444")
    draw.ellipse([s(hx - 1), s(hy - 8), s(hx + 10), s(hy + 3)], fill="#EF4444")
    draw.polygon([(s(hx - 9.5), s(hy + 0.5)), (s(hx + 9.5), s(hy + 0.5)), (s(hx), s(hy + 12))], fill="#EF4444")
    draw_plaque(draw, x1 - 6, y0 + 5, "TRIAL", "#0E7490")


def art_pan_india_nepal(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float]) -> None:
    x0, y0, x1, y1 = box
    rounded_rect(draw, box, radius=5, fill="#FFFBEB", outline="#FDE68A", width=1.0)
    # Himalayan mountains + hydro dam wave + sleek cross-border train bridge
    draw.polygon([(s(x0 + 10), s(y1 - 18)), (s(x0 + 48), s(y0 + 8)), (s(x0 + 86), s(y1 - 18))], fill="#94A3B8")
    draw.polygon([(s(x0 + 36), s(y0 + 16)), (s(x0 + 48), s(y0 + 8)), (s(x0 + 60), s(y0 + 16))], fill="#FFFFFF")
    draw.polygon([(s(x0 + 66), s(y1 - 18)), (s(x0 + 108), s(y0 + 12)), (s(x0 + 150), s(y1 - 18))], fill="#64748B")
    draw.polygon([(s(x0 + 96), s(y0 + 20)), (s(x0 + 108), s(y0 + 12)), (s(x0 + 120), s(y0 + 20))], fill="#FFFFFF")
    # Hydro water + rail bridge
    draw.rectangle([s(x0 + 2), s(y1 - 18), s(x1 - 2), s(y1 - 2)], fill="#0284C7")
    draw.rectangle([s(x0 + 16), s(y1 - 24), s(x1 - 16), s(y1 - 17)], fill="#334155")
    # Sleek orange/white train crossing bridge
    rounded_rect(draw, (x0 + 124, y1 - 36, x0 + 216, y1 - 23), radius=4, fill="#EA580C", outline="#FFFFFF", width=s(1.2))
    for wx in (x0 + 136, x0 + 156, x0 + 176, x0 + 196):
        draw.rectangle([s(wx), s(y1 - 33), s(wx + 12), s(y1 - 27)], fill="#FEF08A")
    draw_plaque(draw, x1 - 6, y0 + 5, "RAIL", "#9D174D")


# ---------- HERO & GALLERY CARD RENDERERS ----------

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


def draw_hero_card(
    draw: ImageDraw.ImageDraw,
    rect: tuple[float, float, float, float],
    header_left: str,
    source_right: str,
    color: str,
    headline: str,
    takeaway: str,
    art_fn: Any,
    audit_boxes: list[tuple[str, tuple[float, float, float, float]]],
) -> None:
    x0, y0, x1, y1 = rect
    hdr_h = 25.0
    rounded_rect(draw, rect, radius=6.5, fill=CARD_BG, outline=HAIRLINE, width=1.1)
    top_rounded_strip(draw, x0 + 0.5, y0 + 0.5, x1 - 0.5, y0 + hdr_h, radius=6.0, fill=color)

    hdr_font = load_font(SANS_BLACK, 15.0)
    lb = draw_left_text(draw, x0 + 9, y0 + hdr_h / 2, header_left, hdr_font, "#FFFFFF")
    rb = draw_right_text(draw, x1 - 9, y0 + hdr_h / 2, source_right, hdr_font, "#FDE68A")
    assert lb[2] + 8.0 <= rb[0], f"Hero header overlap: {header_left} vs {source_right}"

    art_box = (x0 + 6.0, y0 + hdr_h + 6.0, x0 + 124.0, y1 - 6.0)
    art_fn(draw, art_box)

    tx0 = art_box[2] + 9.0
    max_w = x1 - tx0 - 8.0

    h_font = load_font(SERIF_BOLD, 19.5)
    h_lines = wrap_lines(draw, headline, h_font, max_w)
    assert len(h_lines) <= 2, f"Hero headline >2 lines ({h_lines}): {headline}"
    hy = y0 + hdr_h + 19.0
    for i, line in enumerate(h_lines):
        hb = draw_left_text(draw, tx0, hy + i * 24.0, line, h_font, INK)
        assert hb[2] <= x1 - 6.0, f"Hero headline overflow: {line}"
        audit_boxes.append((f"hero_h:{header_left}:{i}", hb))

    t_font = load_font(SANS_BOLD, 15.0)
    tb = draw_left_text(draw, tx0, y1 - 16.0, takeaway, t_font, INK_MUTED)
    assert tb[2] <= x1 - 6.0, f"Hero takeaway overflow: {takeaway}"
    audit_boxes.append((f"hero_t:{header_left}", tb))


def draw_panoramic_card(
    draw: ImageDraw.ImageDraw,
    rect: tuple[float, float, float, float],
    header_left: str,
    source_right: str,
    color: str,
    headline: str,
    art_fn: Any,
    audit_boxes: list[tuple[str, tuple[float, float, float, float]]],
) -> None:
    x0, y0, x1, y1 = rect
    hdr_h = 24.0
    rounded_rect(draw, rect, radius=6.5, fill=CARD_BG, outline=HAIRLINE, width=1.1)
    top_rounded_strip(draw, x0 + 0.5, y0 + 0.5, x1 - 0.5, y0 + hdr_h, radius=6.0, fill=color)

    hdr_font = load_font(SANS_BLACK, 15.0)
    lb = draw_left_text(draw, x0 + 8, y0 + hdr_h / 2, header_left, hdr_font, "#FFFFFF")
    rb = draw_right_text(draw, x1 - 8, y0 + hdr_h / 2, source_right, hdr_font, "#FDE68A")
    assert lb[2] + 8.0 <= rb[0], f"Card header overlap: {header_left} vs {source_right}"

    art_box = (x0 + 6.0, y0 + hdr_h + 5.0, x1 - 6.0, y0 + hdr_h + 65.0)
    art_fn(draw, art_box)

    h_font = load_font(SERIF_BOLD, 18.2)
    max_w = x1 - x0 - 16.0
    h_lines = wrap_lines(draw, headline, h_font, max_w)
    assert len(h_lines) <= 2, f"Panoramic headline >2 lines ({h_lines}): {headline}"
    cy_start = art_box[3] + (16.5 if len(h_lines) == 2 else 27.0)
    for i, line in enumerate(h_lines):
        hb = draw_left_text(draw, x0 + 8.5, cy_start + i * 22.0, line, h_font, INK)
        assert hb[2] <= x1 - 6.0 and hb[3] <= y1 - 3.5, f"Panoramic headline overflow: {line}"
        audit_boxes.append((f"pan_h:{header_left}:{i}", hb))


# ---------- BOTTOM DARK-NAVY 2x7 ATTRIBUTED WIRE (14 CRISP 15px DISPATCHES) ----------

def draw_dark_wire(
    draw: ImageDraw.ImageDraw,
    rect: tuple[float, float, float, float],
    left_rows: list[tuple[str, str, str]],
    right_rows: list[tuple[str, str, str]],
    audit_boxes: list[tuple[str, tuple[float, float, float, float]]],
) -> None:
    x0, y0, x1, y1 = rect
    rounded_rect(draw, rect, radius=6.5, fill=NAVY_DARK, outline=NAVY_MID, width=1.1)
    draw.line([s(x0 + 8), s(y0 + 1), s(x1 - 8), s(y0 + 1)], fill=GOLD, width=s(1.6))

    mid_x = (x0 + x1) / 2
    draw.line([s(mid_x), s(y0 + 7), s(mid_x), s(y1 - 7)], fill="#29425E", width=s(1.2))

    body_font = load_font(SANS_BOLD, 15.0)
    src_font = load_font(SANS_BLACK, 15.0)
    pad_y = 5.0
    row_h = (y1 - y0 - pad_y * 2) / 7.0

    for col_idx, rows in enumerate((left_rows, right_rows)):
        cx0 = (x0 + 10.0) if col_idx == 0 else (mid_x + 10.0)
        cx1 = (mid_x - 10.0) if col_idx == 0 else (x1 - 10.0)
        for r_idx, (text, src, dot_col) in enumerate(rows):
            cy = y0 + pad_y + (r_idx + 0.5) * row_h
            if r_idx > 0:
                ry = y0 + pad_y + r_idx * row_h
                draw.line([s(cx0), s(ry), s(cx1), s(ry)], fill="#1E334B", width=s(0.8))
            draw.rectangle([s(cx0), s(cy - 3.2), s(cx0 + 6.4), s(cy + 3.2)], fill=dot_col)
            tb = draw_left_text(draw, cx0 + 11.5, cy, text, body_font, "#F8FAFC")
            sb = draw_right_text(draw, cx1, cy, src, src_font, GOLD_LIGHT)
            assert tb[2] + 8.0 <= sb[0], f"Wire row collides with source tag: '{text}' vs '{src}' (gap={sb[0] - tb[2]:.1f})"
            audit_boxes.append((f"wire:{col_idx}:{r_idx}:t", tb))
            audit_boxes.append((f"wire:{col_idx}:{r_idx}:s", sb))


# ---------- BOTTOM 15px DATE CHECK EXCLUSION BAR (y=987..1019px) ----------

def draw_date_check_bar(
    draw: ImageDraw.ImageDraw,
    rect: tuple[float, float, float, float],
    audit_boxes: list[tuple[str, tuple[float, float, float, float]]],
) -> None:
    x0, y0, x1, y1 = rect
    cy = (y0 + y1) / 2
    rounded_rect(draw, rect, radius=6.0, fill="#162A40", outline=GOLD, width=1.4)

    badge = (x0 + 5, y0 + 4, x0 + 216, y1 - 4)
    rounded_rect(draw, badge, radius=4.0, fill="#B91C1C")
    draw_centered_text(
        draw,
        (badge[0] + badge[2]) / 2,
        cy,
        "DATE CHECK · 23 NOV UTC",
        load_font(SANS_BLACK, 15.0),
        "#FFFFFF",
    )

    excl = "Excluded 21–22 Nov: COP31 talks; Vegas F1; Premier League; ATP Finals; BepiColombo"
    eb = draw_left_text(draw, badge[2] + 10.0, cy, excl, load_font(SANS_BOLD, 15.0), "#F8FAFC")
    assert eb[2] <= x1 - 6.0, f"Date-check bar clipped: right={eb[2]:.1f} > {x1 - 6.0}"
    audit_boxes.append(("date_check", eb))


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


# ---------- PROGRAMMATIC LAYOUT & DATE-SAFETY AUDIT ----------

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
    print(f"Layout audit: 0 issues ({len(boxes)} boxes checked, MIN_FONT_PX={MIN_FONT_PX}, {len(all_story_texts)} stories date-clean)")


# ---------- MAIN RENDER PIPELINE ----------

def render() -> None:
    img = Image.new("RGB", (CW, CH), PAPER)
    draw = ImageDraw.Draw(img)
    audit_boxes: list[tuple[str, tuple[float, float, float, float]]] = []
    all_story_texts: list[str] = []

    # 1. Top Masthead (y=0..76px)
    draw.rectangle([0, 0, CW, s(24)], fill=NAVY_DARK)
    draw_centered_text(
        draw,
        WIDTH / 2,
        12.0,
        "WORLD NEWS ATLAS  ·  25 SOURCED STORIES  ·  7 REGIONS  ·  23 NOV 2026 UTC",
        load_font(SANS_BLACK, 15.0),
        GOLD_LIGHT,
    )
    draw_centered_text(
        draw,
        WIDTH / 2,
        48.5,
        "Monday 23 November 2026",
        load_font(SERIF_BOLD, 44.0),
        INK,
    )
    draw.line([s(10), s(73.5), s(WIDTH - 10), s(73.5)], fill=INK, width=s(2.0))
    draw.line([s(10), s(76.0), s(WIDTH - 10), s(76.0)], fill=GOLD, width=s(1.0))

    # 2. Hero Visual Band (y=79..331px): Airy World Map + 2 Giant Hero Leads
    draw_world_map(draw, (10, 79, 566, 331), audit_boxes)

    heroes = [
        (
            "LEAD 1 · GLOBAL · MARKETS",
            "REUTERS",
            REGION_COLORS["GLOBAL"],
            "AI Rout Hits Asia; Korea & Taiwan Act",
            "Kospi -3.3%; Seoul readies $8B fund",
            art_hero_asia,
        ),
        (
            "LEAD 2 · M. EAST · OIL",
            "AFP",
            REGION_COLORS["MIDDLE_EAST"],
            "Iran Vows 'All Tools' on U.S. Blockade",
            "Tehran answers U.S. fire warning to ships",
            art_hero_iran,
        ),
    ]
    for idx, (hl, sr, col, head, take, art_fn) in enumerate(heroes):
        ry0 = 79.0 + idx * (123.0 + 6.0)
        draw_hero_card(draw, (576.0, ry0, 1014.0, ry0 + 123.0), hl, sr, col, head, take, art_fn, audit_boxes)
        all_story_texts.append(f"{head} {take}")

    # 3. 3x3 Giant Panoramic Museum Gallery (y=337..787px): 9 Large Illustrated Cards
    gallery = [
        ("EUROPE · UKRAINE", "EU", REGION_COLORS["EUROPE"], "EU Disburses €7.9B Under Ukraine Facility", art_pan_ukraine),
        ("EUROPE · ENERGY", "FT", REGION_COLORS["EUROPE"], "European Gas Surges 6% to €93/MWh", art_pan_gas),
        ("AFRICA · OIL", "AA", REGION_COLORS["AFRICA"], "Libya NOC: Sharara Shut Cuts 350k bpd", art_pan_libya),
        ("AMERICAS · ECON", "AP", REGION_COLORS["AMERICAS"], "Bessent Warns Hawkish Fed Risks Growth", art_pan_fed),
        ("ASIA · FINANCE", "MAS", REGION_COLORS["ASIA"], "Singapore & China Expand RMB Hub", art_pan_rmb),
        ("S. AMERICA · SPACE", "ARIANE", REGION_COLORS["S_AMERICA"], "Ariane 6 Launch Halted in French Guiana", art_pan_ariane),
        ("AFRICA · HEALTH", "CDC", REGION_COLORS["AFRICA"], "Africa Health Summit Opens in Addis", art_pan_cphia),
        ("GLOBAL · MEDICINE", "NOVARTIS", REGION_COLORS["SCIENCE"], "Novartis Says Heart Trial Met Endpoint", art_pan_heart),
        ("S. ASIA · TRADE", "HINDU", REGION_COLORS["ASIA"], "India & Nepal Sign Rail & Hydro Pacts", art_pan_india_nepal),
    ]
    gx0, gy0 = 10.0, 337.0
    gw, gh = 328.0, 146.0
    ggap_x, ggap_y = 10.0, 6.0
    for idx, (hl, sr, col, head, art_fn) in enumerate(gallery):
        r, c = divmod(idx, 3)
        rx0 = gx0 + c * (gw + ggap_x)
        ry0 = gy0 + r * (gh + ggap_y)
        draw_panoramic_card(draw, (rx0, ry0, rx0 + gw, ry0 + gh), hl, sr, col, head, art_fn, audit_boxes)
        all_story_texts.append(head)

    # 4. Bottom Dark-Navy 2x7 Sourced Wire (y=793..983px): 14 Single-Line 15px Dispatches
    left_wire = [
        ("Belgium: Strike halts skies 07–21 UTC", "AVI-GO", REGION_COLORS["EUROPE"]),
        ("UK: Report warns BBC fee <50% homes", "GUARDIAN", REGION_COLORS["EUROPE"]),
        ("EU: Living-cost protests hit capitals", "ALJAZEERA", REGION_COLORS["EUROPE"]),
        ("Canada: Bombardier votes 97.8% strike", "AVI-GO", REGION_COLORS["AMERICAS"]),
        ("Colombia: NGO warns Chocó malaria +46%", "STC", REGION_COLORS["S_AMERICA"]),
        ("Australia: Chalmers sees <2% growth", "GUARDIAN", REGION_COLORS["OCEANIA"]),
        ("Vanuatu: USGS logs M6.5 deep quake", "USGS", REGION_COLORS["OCEANIA"]),
    ]
    right_wire = [
        ("Gaza: Oxfam warns 99% faces toxic risk", "OXFAM", REGION_COLORS["MIDDLE_EAST"]),
        ("Gulf: Saudi & Japan add 16M bbl oil", "MUFG", REGION_COLORS["MIDDLE_EAST"]),
        ("Hormuz: Monitors cite Gulf ship attacks", "JPOST", REGION_COLORS["MIDDLE_EAST"]),
        ("Ivory Coast: Steinmeier opens tour", "DPA", REGION_COLORS["AFRICA"]),
        ("AfCFTA: S. Africa & Zambia link trade", "SARS", REGION_COLORS["AFRICA"]),
        ("Seoul: New foreign min.; Qatar LNG", "K.HERALD", REGION_COLORS["ASIA"]),
        ("Sport: NZ holds India to Test draw", "ICC", REGION_COLORS["OCEANIA"]),
    ]
    for rows in (left_wire, right_wire):
        for txt, src, _ in rows:
            all_story_texts.append(f"{txt} ({src})")
    draw_dark_wire(draw, (10, 793, 1014, 983), left_wire, right_wire, audit_boxes)

    # 5. Bottom High-Contrast 15px DATE CHECK Bar (y=987..1019px)
    draw_date_check_bar(draw, (10, 987, 1014, 1019), audit_boxes)

    assert len(all_story_texts) == 25, f"Expected 25 stories, got {len(all_story_texts)}"
    audit_layout(audit_boxes, all_story_texts)

    # Downsample 2x -> 1x with BOX area average (zero ringing, sharp edges)
    final_img = img.resize((WIDTH, HEIGHT), Image.Resampling.BOX)
    nbytes = save_compact_rgb_png(final_img, OUT_PNG)
    print(f"Rendered {OUT_PNG}: {WIDTH}x{HEIGHT} RGB PNG, {nbytes:,} bytes ({nbytes / 1024:.1f} KiB)")
    assert nbytes < 1_048_576, f"PNG exceeds 1 MiB: {nbytes}"


if __name__ == "__main__":
    render()
