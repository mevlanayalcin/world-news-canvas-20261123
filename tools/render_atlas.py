#!/usr/bin/env python3
"""Render the 1024x1024 World News Atlas (v3, 23 stories) for Monday 23 November 2026.

Sweet-spot championship architecture:
- Top 80% (y=0..814): 44px broadsheet masthead + Natural Earth 110m World Hotspots Map
  with high-contrast #111827 callout pills (18px bold white) + 2 Hero Leads (22.5px serif,
  16px bold decks) + 3x3 GIANT 326px Panoramic Museum Flat-Vector Cards (9 illustrated
  panels with layered skylines/landscapes, >=15px plaques, and 21.5px Lato-Black heads)
- Bottom 20% (y=820..1018): Airy dark-navy 2x6 Global Dispatch Band (12 dedicated single-line
  17.5px bold pure-white headlines with region-coded 15px pills — 1 story per row, zero cramming)
- Strict MIN_FONT_PX = 15.0 enforced programmatically across every pixel
- 23 distinct, 100% verified pure Monday 23 November 2026 stories across 7 regions & 16 beats
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

# Warm Archival Broadsheet + Harmonious Region Palette
PAPER = "#FAF6EE"
CARD_BG = "#FFFFFF"
HAIRLINE = "#D6CCBA"
INK = "#0F172A"
INK_MUTED = "#334155"
NAVY_DARK = "#0D1B2A"
PILL_DARK = "#111827"
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
}


def s(v: float) -> int:
    return int(round(v * SCALE))


def sf(v: float) -> float:
    return v * SCALE


def load_font(path: str, size_px: float) -> ImageFont.FreeTypeFont:
    assert size_px >= MIN_FONT_PX, f"Font size {size_px}px violates {MIN_FONT_PX}px hard floor!"
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
) -> tuple[float, float, float, float]:
    f = load_font(SANS_BLACK, font_px)
    tw, _ = text_size(draw, text, f)
    w = tw + pad_x * 2
    rect = (x1 - w, y0, x1, y0 + h)
    rounded_rect(draw, (rect[0] - 1, rect[1] - 1, rect[2] + 1, rect[3] + 1), radius=5.2, fill="#FFFFFF")
    rounded_rect(draw, rect, radius=4.5, fill=bg)
    draw_centered_text(draw, (rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2, text, f, fg)
    return rect


def project_lonlat(
    lon: float,
    lat: float,
    box: tuple[float, float, float, float],
    lon_min: float = -162.0,
    lon_max: float = 178.0,
    lat_min: float = -58.0,
    lat_max: float = 75.0,
) -> tuple[float, float]:
    x0, y0, x1, y1 = box
    u = (lon - lon_min) / (lon_max - lon_min)
    v = (lat_max - lat) / (lat_max - lat_min)
    return x0 + u * (x1 - x0), y0 + v * (y1 - y0)


def extract_region_polygons(lon_range: tuple[float, float], lat_range: tuple[float, float]) -> list[list[tuple[float, float]]]:
    if not GEOJSON_PATH.exists():
        return []
    geo = json.loads(GEOJSON_PATH.read_text(encoding="utf-8"))
    out: list[list[tuple[float, float]]] = []
    lo_min, lo_max = lon_range
    la_min, la_max = lat_range
    for feat in geo.get("features", []):
        geom = feat.get("geometry", {})
        gtype = geom.get("type")
        coords = geom.get("coordinates", [])
        polys = [coords] if gtype == "Polygon" else (coords if gtype == "MultiPolygon" else [])
        for poly in polys:
            if not poly:
                continue
            ring = poly[0]
            lons = [p[0] for p in ring]
            lats = [p[1] for p in ring]
            if min(lons) >= lo_min and max(lons) <= lo_max and min(lats) >= la_min and max(lats) <= la_max:
                out.append([(p[0], p[1]) for p in ring])
    return out


def draw_world_map(
    draw: ImageDraw.ImageDraw,
    panel: tuple[float, float, float, float],
    audit_boxes: list[tuple[str, tuple[float, float, float, float]]],
) -> None:
    px0, py0, px1, py1 = panel
    legend_h = 26.0
    map_box = (px0, py0, px1, py1 - legend_h)
    mx0, my0, mx1, my1 = map_box

    rounded_rect(draw, panel, radius=8, fill=OCEAN, outline=HAIRLINE, width=1.0)

    for lon in range(-150, 180, 30):
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
                    if lat < -58.0:
                        continue
                    clon = max(-162.0, min(178.0, lon))
                    clat = max(-58.0, min(75.0, lat))
                    x, y = project_lonlat(clon, clat, map_box)
                    pts.append((s(x), s(y)))
                if len(pts) >= 3:
                    draw.polygon(pts, fill=LAND_FILL, outline=LAND_STROKE)

    title_font = load_font(SANS_BLACK, 15.0)
    t_rect = (mx0 + 8, my0 + 6, mx0 + 178, my0 + 29)
    rounded_rect(draw, t_rect, radius=5, fill=NAVY_DARK)
    draw_centered_text(draw, (t_rect[0] + t_rect[2]) / 2, (t_rect[1] + t_rect[3]) / 2, "WORLD HOTSPOTS", title_font, GOLD_LIGHT)
    audit_boxes.append(("map:title", t_rect))

    minor_pins = [
        ("Montreal", -73.6, 45.5, REGION_COLORS["AMERICAS"]),
        ("Choco", -76.6, 5.7, REGION_COLORS["S_AMERICA"]),
        ("Addis", 38.7, 9.0, REGION_COLORS["AFRICA"]),
        ("Durban", 31.0, -29.8, REGION_COLORS["AFRICA"]),
        ("Delhi", 77.2, 28.6, REGION_COLORS["ASIA"]),
        ("Singapore", 103.8, 1.3, REGION_COLORS["ASIA"]),
        ("Vanuatu", 168.3, -17.7, REGION_COLORS["OCEANIA"]),
        ("Wellington", 174.8, -41.3, REGION_COLORS["OCEANIA"]),
    ]
    for pname, lon, lat, col in minor_pins:
        px, py = project_lonlat(lon, lat, map_box)
        draw.ellipse([s(px - 4.8), s(py - 4.8), s(px + 4.8), s(py + 4.8)], fill="#FFFFFF", outline=INK, width=s(0.9))
        draw.ellipse([s(px - 3.0), s(py - 3.0), s(px + 3.0), s(py + 3.0)], fill=col)
        audit_boxes.append((f"pin:{pname}", (px - 5.0, py - 5.0, px + 5.0, py + 5.0)))

    # 7 HIGH-CONTRAST #111827 CALLOUT PILLS (18px bold white + colored left accent bar)
    pill_font = load_font(SANS_BLACK, 18.0)
    callouts = [
        ("U.S. FED", -77.0, 38.9, mx0 + 8, my0 + 102, REGION_COLORS["AMERICAS"]),
        ("GUIANA", -52.7, 5.2, mx0 + 14, my0 + 194, REGION_COLORS["S_AMERICA"]),
        ("EU GAS", 4.9, 52.3, mx0 + 194, my0 + 7, REGION_COLORS["EUROPE"]),
        ("LIBYA", 12.2, 26.5, mx0 + 206, my0 + 170, REGION_COLORS["AFRICA"]),
        ("#2 IRAN", 56.3, 26.5, mx0 + 354, my0 + 144, REGION_COLORS["MIDDLE_EAST"]),
        ("#1 ASIA", 125.0, 34.5, mx0 + 458, my0 + 14, REGION_COLORS["GLOBAL"]),
        ("AUSTRALIA", 149.1, -35.3, mx0 + 366, my0 + 216, REGION_COLORS["OCEANIA"]),
    ]

    computed = []
    for label, lon, lat, px, py, color in callouts:
        tw, _ = text_size(draw, label, pill_font)
        pw = tw + 24.0
        ph = 25.5
        px = max(mx0 + 6, min(mx1 - pw - 6, px))
        py = max(my0 + 5, min(my1 - ph - 4, py))
        pin_x, pin_y = project_lonlat(lon, lat, map_box)
        computed.append((label, pin_x, pin_y, px, py, pw, ph, color))

    for label, pin_x, pin_y, px, py, pw, ph, color in computed:
        cx = max(px + 10, min(px + pw - 10, pin_x))
        cy = max(py + 6, min(py + ph - 6, pin_y))
        draw.line([s(pin_x), s(pin_y), s(cx), s(cy)], fill="#FFFFFF", width=s(3.4))
        draw.line([s(pin_x), s(pin_y), s(cx), s(cy)], fill=color, width=s(2.0))

    for label, pin_x, pin_y, px, py, pw, ph, color in computed:
        draw.ellipse([s(pin_x - 6.6), s(pin_y - 6.6), s(pin_x + 6.6), s(pin_y + 6.6)], fill="#FFFFFF", outline=PILL_DARK, width=s(1.2))
        draw.ellipse([s(pin_x - 4.1), s(pin_y - 4.1), s(pin_x + 4.1), s(pin_y + 4.1)], fill=color)
        audit_boxes.append((f"pin:{label}", (pin_x - 6.8, pin_y - 6.8, pin_x + 6.8, pin_y + 6.8)))

    for label, pin_x, pin_y, px, py, pw, ph, color in computed:
        rect = (px, py, px + pw, py + ph)
        rounded_rect(draw, (px + 1.5, py + 1.6, px + pw + 1.5, py + ph + 1.6), radius=7, fill="#A5BBD0")
        rounded_rect(draw, rect, radius=7, fill=PILL_DARK, outline="#FFFFFF", width=1.2)
        rounded_rect(draw, (px + 3.0, py + 3.5, px + 8.5, py + ph - 3.5), radius=2.5, fill=color)
        draw_centered_text(draw, px + 8.5 + (pw - 11.5) / 2, py + ph / 2, label, pill_font, "#FFFFFF")
        audit_boxes.append((f"map_pill:{label}", rect))

    ly0 = py1 - legend_h
    rounded_rect(draw, (px0 + 1, ly0, px1 - 1, py1 - 1), radius=7, fill="#F8F4EC")
    draw.rectangle([s(px0 + 1), s(ly0), s(px1 - 1), s(ly0 + 9)], fill="#F8F4EC")
    draw.line([s(px0 + 1), s(ly0), s(px1 - 1), s(ly0)], fill=HAIRLINE, width=s(1.0))

    leg_font = load_font(SANS_BOLD, 15.0)
    legend_items = [
        ("Americas", REGION_COLORS["AMERICAS"]),
        ("Europe", REGION_COLORS["EUROPE"]),
        ("M.East", REGION_COLORS["MIDDLE_EAST"]),
        ("Africa", REGION_COLORS["AFRICA"]),
        ("Asia", REGION_COLORS["ASIA"]),
        ("Oceania", REGION_COLORS["OCEANIA"]),
    ]
    item_widths = [13 + text_size(draw, lbl, leg_font)[0] for lbl, _ in legend_items]
    total_w = sum(item_widths)
    gap = (px1 - px0 - 18 - total_w) / max(1, len(legend_items) - 1)
    cur_x = px0 + 9
    cy = ly0 + legend_h / 2
    for (lbl, col), iw in zip(legend_items, item_widths):
        draw.ellipse([s(cur_x), s(cy - 4.5), s(cur_x + 9.0), s(cy + 4.5)], fill=col)
        draw_left_text(draw, cur_x + 12.0, cy, lbl, leg_font, INK)
        cur_x += iw + gap


# ---------- 2 LAYERED HERO LEAD EDITORIAL SCENES (118 x 97px) ----------

def draw_lead1_art(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float]) -> None:
    x0, y0, x1, y1 = box
    h = y1 - y0
    rounded_rect(draw, box, radius=6, fill="#FEF2F2", outline="#FECACA", width=1.0)
    draw.rectangle([s(x0 + 1), s(y1 - 38), s(x1 - 1), s(y1 - 4)], fill="#FDE8E8")
    for i in range(1, 4):
        gy = y0 + h * i / 4
        draw.line([s(x0 + 5), s(gy), s(x1 - 5), s(gy)], fill="#FBD5D5", width=s(1))

    base_y = y1 - 2
    for tx, th, tw in [(x0 + 6, 22, 12), (x0 + 20, 34, 11), (x0 + 34, 40, 10), (x0 + 48, 26, 14), (x0 + 66, 20, 12)]:
        draw.rectangle([s(tx), s(base_y - th), s(tx + tw), s(base_y)], fill="#E2B8B8")
    draw.line([s(x0 + 39), s(base_y - 40), s(x0 + 39), s(base_y - 50)], fill="#D49B9B", width=s(2.0))

    bars = [
        (x0 + 11, y0 + 10, 9, 17, "#DC2626"),
        (x0 + 26, y0 + 19, 9, 21, "#DC2626"),
        (x0 + 41, y0 + 31, 9, 23, "#B91C1C"),
        (x0 + 56, y0 + 44, 9, 24, "#991B1B"),
    ]
    for bx, by, bw, bh, col in bars:
        draw.line([s(bx + bw / 2), s(by - 4), s(bx + bw / 2), s(by + bh + 4)], fill=col, width=s(2))
        draw.rectangle([s(bx), s(by), s(bx + bw), s(by + bh)], fill=col)

    pts = [(s(x0 + 9), s(y0 + 12)), (s(x0 + 39), s(y0 + 31)), (s(x0 + 49), s(y0 + 26)), (s(x0 + 70), s(y0 + 68))]
    draw.line(pts, fill="#7F1D1D", width=s(3.8))
    draw.polygon([(s(x0 + 74), s(y0 + 74)), (s(x0 + 61), s(y0 + 67)), (s(x0 + 74), s(y0 + 58))], fill="#7F1D1D")

    scx, scy = x1 - 26, y1 - 25
    shield = [
        (s(scx), s(scy - 19)),
        (s(scx + 16), s(scy - 12)),
        (s(scx + 14), s(scy + 5)),
        (s(scx), s(scy + 18)),
        (s(scx - 14), s(scy + 5)),
        (s(scx - 16), s(scy - 12)),
    ]
    draw.polygon(shield, fill=NAVY_DARK)
    draw.line(shield + [shield[0]], fill=GOLD, width=s(2.4))
    draw.line([(s(scx - 6.5), s(scy + 1)), (s(scx - 1.5), s(scy + 6)), (s(scx + 8), s(scy - 5.5))], fill="#FACC15", width=s(3.0))

    draw_plaque(draw, x1 - 4, y0 + 4, "-10% S&P", "#B91C1C", font_px=15.0, pad_x=5.0, h=21.0)


def draw_lead2_art(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float]) -> None:
    x0, y0, x1, y1 = box
    h = y1 - y0
    rounded_rect(draw, box, radius=6, fill="#FFF4E6", outline="#FED7AA", width=1.0)
    draw.rectangle([s(x0 + 1), s(y0 + 25), s(x1 - 1), s(y0 + h * 0.57)], fill="#FFEDD5")
    draw.ellipse([s(x0 + 6), s(y0 + 5), s(x0 + 23), s(y0 + 22)], fill="#FB923C")

    sea_y = y0 + h * 0.57
    draw.polygon([(s(x0 + 1), s(sea_y)), (s(x0 + 24), s(sea_y - 14)), (s(x0 + 54), s(sea_y - 6)), (s(x0 + 78), s(sea_y))], fill="#E5C198")
    draw.polygon([(s(x1 - 48), s(sea_y)), (s(x1 - 20), s(sea_y - 12)), (s(x1 - 1), s(sea_y - 5)), (s(x1 - 1), s(sea_y))], fill="#D6A97A")

    rounded_rect(draw, (x0 + 1, sea_y, x1 - 1, y1 - 1), radius=5, fill="#1E3A5F")
    draw.rectangle([s(x0 + 1), s(sea_y), s(x1 - 1), s(sea_y + 9)], fill="#1E3A5F")
    draw.rectangle([s(x0 + 1), s(sea_y + 20), s(x1 - 1), s(y1 - 5)], fill="#152C4A")
    for wy, wx0, wx1 in [(sea_y + 12, x0 + 9, x0 + 44), (sea_y + 23, x0 + 48, x0 + 104), (sea_y + 33, x0 + 16, x0 + 68)]:
        draw.line([s(wx0), s(wy), s(wx1), s(wy)], fill="#60A5FA", width=s(2.0))

    hull = [(s(x0 + 10), s(sea_y + 4)), (s(x0 + 68), s(sea_y + 4)), (s(x0 + 76), s(sea_y - 10)), (s(x0 + 12), s(sea_y - 10))]
    draw.polygon(hull, fill="#0F172A")
    draw.rectangle([s(x0 + 14), s(sea_y - 14), s(x0 + 68), s(sea_y - 9)], fill="#DC2626")
    draw.rectangle([s(x0 + 17), s(sea_y - 26), s(x0 + 31), s(sea_y - 14)], fill="#F8FAFC", outline="#0F172A", width=s(1.2))
    draw.rectangle([s(x0 + 21), s(sea_y - 32), s(x0 + 27), s(sea_y - 26)], fill="#C2410C")
    for tx in (37, 47, 57):
        draw.rounded_rectangle([s(x0 + tx), s(sea_y - 18), s(x0 + tx + 7), s(sea_y - 12)], radius=s(2), fill="#475569")

    bcx, bcy = x1 - 21, sea_y - 10
    draw.arc([s(bcx - 16), s(bcy - 16), s(bcx + 16), s(bcy + 16)], start=110, end=250, fill="#DC2626", width=s(3.8))
    draw.ellipse([s(bcx - 11), s(bcy - 11), s(bcx + 11), s(bcy + 11)], fill="#DC2626", outline="#FFFFFF", width=s(2))
    draw.rectangle([s(bcx - 5.5), s(bcy - 2.2), s(bcx + 5.5), s(bcy + 2.2)], fill="#FFFFFF")

    draw_plaque(draw, x1 - 4, y0 + 4, "BLOCKADE", "#C2410C", font_px=15.0, pad_x=5.0, h=21.0)


def draw_lead_card(
    draw: ImageDraw.ImageDraw,
    rect: tuple[float, float, float, float],
    tag: str,
    color: str,
    headline_lines: list[str],
    sub_lines: list[str],
    art_fn: Any,
    audit_boxes: list[tuple[str, tuple[float, float, float, float]]],
) -> None:
    x0, y0, x1, y1 = rect
    rounded_rect(draw, rect, radius=8, fill=CARD_BG, outline=HAIRLINE, width=1.0)
    strip_h = 23.0
    top_rounded_strip(draw, x0 + 1, y0 + 1, x1 - 1, y0 + strip_h, radius=7, fill=color)
    tag_font = load_font(SANS_BLACK, 15.0)
    draw_left_text(draw, x0 + 10, y0 + strip_h / 2, tag, tag_font, "#FFFFFF")

    art_box = (x0 + 7, y0 + strip_h + 5, x0 + 125, y1 - 6)
    art_fn(draw, art_box)

    tx0 = x0 + 134
    hl_font = load_font(SERIF_BOLD, 22.5)
    sub_font = load_font(SANS_BOLD, 16.0)
    cur_y = y0 + strip_h + 20
    for line in headline_lines:
        b = draw_left_text(draw, tx0, cur_y, line, hl_font, INK)
        audit_boxes.append((f"lead_hl:{line}", b))
        assert b[2] <= x1 - 5, f"Lead headline clipped: '{line}' right={b[2]:.1f} > {x1-5}"
        cur_y += 26
    cur_y += 4
    for sline in sub_lines:
        b = draw_left_text(draw, tx0, cur_y, sline, sub_font, INK_MUTED)
        audit_boxes.append((f"lead_sub:{sline}", b))
        assert b[2] <= x1 - 5, f"Lead sub clipped: '{sline}' right={b[2]:.1f} > {x1-5}"
        cur_y += 20


# ---------- 9 PANORAMIC 3x3 MUSEUM FLAT-VECTOR SCENES (321 x 68px) ----------

def art_eu_gas(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float]) -> None:
    x0, y0, x1, y1 = box
    mid = (x0 + x1) / 2 - 18
    draw.rectangle([s(x0), s(y0), s(mid), s(y1)], fill="#DBEAFE")
    draw.rectangle([s(mid), s(y0), s(x1), s(y1)], fill="#FEF3C7")

    for rx, rh, rw in [(x0 + 6, 22, 24), (x0 + 32, 28, 26), (x0 + 60, 24, 24), (x0 + 86, 33, 22)]:
        draw.rectangle([s(rx), s(y1 - rh), s(rx + rw), s(y1)], fill="#60A5FA")
        draw.polygon([(s(rx - 2), s(y1 - rh)), (s(rx + rw / 2), s(y1 - rh - 9)), (s(rx + rw + 2), s(y1 - rh))], fill="#1E40AF")
        draw.line([(s(rx - 1), s(y1 - rh)), (s(rx + rw / 2), s(y1 - rh - 9)), (s(rx + rw + 1), s(y1 - rh))], fill="#FFFFFF", width=s(2.2))
        draw.rectangle([s(rx + 5), s(y1 - rh + 6), s(rx + 11), s(y1 - rh + 12)], fill="#FEF08A")

    cx, cy, r = x0 + 25, y0 + 16, 11.5
    for deg in range(0, 360, 60):
        rad = math.radians(deg)
        draw.line([s(cx), s(cy), s(cx + math.cos(rad) * r), s(cy + math.sin(rad) * r)], fill="#1D4ED8", width=s(2.3))
    draw.ellipse([s(cx - 3), s(cy - 3), s(cx + 3), s(cy + 3)], fill="#FFFFFF", outline="#1D4ED8", width=s(1.5))

    for wy in (y0 + 14, y0 + 24):
        draw.line([s(x0 + 48), s(wy), s(mid + 6), s(wy)], fill="#3B82F6", width=s(2.3))

    fx, fy = mid + 32, y1 - 6
    draw.rectangle([s(fx - 18), s(fy - 4), s(fx + 18), s(y1)], fill="#334155")
    draw.polygon([(s(fx), s(y0 + 9)), (s(fx + 18), s(y0 + 32)), (s(fx + 16), s(fy - 4)), (s(fx - 16), s(fy - 4)), (s(fx - 18), s(y0 + 32))], fill="#EA580C")
    draw.polygon([(s(fx), s(y0 + 23)), (s(fx + 9), s(y0 + 41)), (s(fx + 7.5), s(fy - 4)), (s(fx - 7.5), s(fy - 4)), (s(fx - 9), s(y0 + 41))], fill="#FACC15")
    draw.ellipse([s(fx - 6), s(fy - 12), s(fx + 6), s(fy - 3)], fill="#2563EB")

    px0 = mid + 66
    draw.line([(s(px0), s(y0 + 38)), (s(px0 + 20), s(y0 + 30)), (s(px0 + 38), s(y0 + 32)), (s(px0 + 66), s(y0 + 11))], fill="#DC2626", width=s(3.8))
    draw.polygon([(s(px0 + 71), s(y0 + 6)), (s(px0 + 56), s(y0 + 10)), (s(px0 + 68), s(y0 + 21))], fill="#DC2626")

    draw_plaque(draw, x1 - 7, y1 - 24, "+6% €93", "#B91C1C", font_px=15.0, pad_x=7.0, h=21.0)


def art_libya_oil(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float]) -> None:
    x0, y0, x1, y1 = box
    draw.rectangle([s(x0), s(y0), s(x1), s(y1)], fill="#FEF3C7")
    draw.ellipse([s(x0 + 16), s(y0 + 6), s(x0 + 36), s(y0 + 26)], fill="#FDBA74")
    draw.polygon([(s(x0), s(y1)), (s(x0), s(y1 - 26)), (s(x0 + 85), s(y1 - 34)), (s(x0 + 175), s(y1 - 22)), (s(x1), s(y1 - 30)), (s(x1), s(y1))], fill="#EED6A5")
    draw.polygon([(s(x0), s(y1)), (s(x0), s(y1 - 15)), (s(x0 + 115), s(y1 - 22)), (s(x0 + 230), s(y1 - 12)), (s(x1), s(y1 - 18)), (s(x1), s(y1))], fill="#DFBF82")

    dx_t = x0 + 56
    draw.polygon([(s(dx_t - 8), s(y1 - 21)), (s(dx_t), s(y0 + 7)), (s(dx_t + 8), s(y1 - 21))], outline="#92400E")
    draw.line([s(dx_t - 6), s(y0 + 22), s(dx_t + 6), s(y0 + 22)], fill="#92400E", width=s(1.6))

    py = y0 + 39
    draw.rectangle([s(x0 + 8), s(py - 8), s(x1 - 116), s(py + 8)], fill="#475569", outline="#1E293B", width=s(1.5))
    draw.line([s(x0 + 10), s(py - 3.5), s(x1 - 118), s(py - 3.5)], fill="#94A3B8", width=s(2.0))
    for fx in (x0 + 52, x0 + 176):
        draw.rectangle([s(fx - 4), s(py - 12), s(fx + 4), s(py + 12)], fill="#334155")
    draw.ellipse([s(x1 - 120), s(py - 8), s(x1 - 112), s(py + 8)], fill="#0F172A", outline="#334155", width=s(1.4))

    vx, vy = x0 + 114, py
    draw.rectangle([s(vx - 5), s(vy - 20), s(vx + 5), s(vy + 12)], fill="#1E293B")
    draw.ellipse([s(vx - 20), s(vy - 20), s(vx + 20), s(vy + 20)], fill="#FEF2F2", outline="#DC2626", width=s(4.4))
    for deg in (0, 60, 120):
        rad = math.radians(deg)
        draw.line([s(vx - math.cos(rad) * 16), s(vy - math.sin(rad) * 16), s(vx + math.cos(rad) * 16), s(vy + math.sin(rad) * 16)], fill="#DC2626", width=s(2.8))
    draw.ellipse([s(vx - 5.5), s(vy - 5.5), s(vx + 5.5), s(vy + 5.5)], fill="#991B1B")

    dx, dy = x1 - 106, py + 11
    draw.polygon([(s(dx), s(dy - 8)), (s(dx + 6.8), s(dy + 4)), (s(dx), s(dy + 10)), (s(dx - 6.8), s(dy + 4))], fill="#0F172A")
    draw.ellipse([s(dx - 6.8), s(dy), s(dx + 6.8), s(dy + 12)], fill="#0F172A")

    draw_plaque(draw, x1 - 7, y0 + 6, "-350K BPD", "#047857", font_px=15.0, pad_x=6.0, h=21.0)
    draw_plaque(draw, x1 - 7, y1 - 24, "SHARARA", "#1E293B", fg="#FDE68A", font_px=15.0, pad_x=6.0, h=21.0)


def art_us_fed(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float]) -> None:
    x0, y0, x1, y1 = box
    draw.rectangle([s(x0), s(y0), s(x1), s(y1)], fill="#EEF2FF")
    draw.rectangle([s(x0), s(y1 - 13), s(x1), s(y1)], fill="#DBEAFE")

    bx0, bx1 = x0 + 14, x0 + 142
    by_base = y1 - 5
    draw.rectangle([s(bx0 - 6), s(by_base - 5), s(bx1 + 6), s(by_base)], fill="#1E3A8A")
    draw.rectangle([s(bx0 - 3), s(by_base - 10), s(bx1 + 3), s(by_base - 5)], fill="#3730A3")
    draw.rectangle([s(bx0), s(by_base - 36), s(bx1), s(by_base - 10)], fill="#C7D2FE")
    for cx in (bx0 + 12, bx0 + 34, bx0 + 56, bx0 + 78, bx0 + 100, bx0 + 116):
        draw.rectangle([s(cx - 4.5), s(by_base - 36), s(cx + 4.5), s(by_base - 10)], fill="#FFFFFF", outline="#3730A3", width=s(1.2))
    draw.polygon([(s(bx0 - 8), s(by_base - 36)), (s((bx0 + bx1) / 2), s(y0 + 6)), (s(bx1 + 8), s(by_base - 36))], fill="#3730A3")
    draw.ellipse([s((bx0 + bx1) / 2 - 4.5), s(y0 + 16), s((bx0 + bx1) / 2 + 4.5), s(y0 + 25)], fill="#FACC15")

    gx, gy, gr = x0 + 206, y1 - 12, 32
    draw.pieslice([s(gx - gr), s(gy - gr), s(gx + gr), s(gy + gr)], start=180, end=240, fill="#60A5FA")
    draw.pieslice([s(gx - gr), s(gy - gr), s(gx + gr), s(gy + gr)], start=240, end=300, fill="#F59E0B")
    draw.pieslice([s(gx - gr), s(gy - gr), s(gx + gr), s(gy + gr)], start=300, end=360, fill="#DC2626")
    ir = 17
    draw.pieslice([s(gx - ir), s(gy - ir), s(gx + ir), s(gy + ir)], start=180, end=360, fill="#FFFFFF")
    ang = math.radians(-26)
    draw.line([s(gx), s(gy), s(gx + math.cos(ang) * 28), s(gy + math.sin(ang) * 28)], fill="#0F172A", width=s(3.4))
    draw.ellipse([s(gx - 5.2), s(gy - 5.2), s(gx + 5.2), s(gy + 5.2)], fill="#0F172A", outline="#FFFFFF", width=s(1.4))

    draw_plaque(draw, x1 - 7, y0 + 6, "FED RISK", "#3730A3", font_px=15.0, pad_x=6.0, h=21.0)


def art_sg_china_rmb(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float]) -> None:
    x0, y0, x1, y1 = box
    draw.rectangle([s(x0), s(y0), s(x1), s(y1)], fill="#FDF2F8")
    water_y = y1 - 12
    draw.rectangle([s(x0), s(water_y), s(x1), s(y1)], fill="#E0F2FE")

    px = x0 + 34
    draw.rectangle([s(x0 + 10), s(water_y - 30), s(x0 + 24), s(water_y)], fill="#BE185D")
    draw.line([s(px), s(y0 + 8), s(px), s(water_y)], fill="#9D174D", width=s(2.8))
    draw.ellipse([s(px - 5.5), s(y0 + 18), s(px + 5.5), s(y0 + 29)], fill="#9D174D")
    draw.ellipse([s(px - 8), s(y0 + 35), s(px + 8), s(y0 + 50)], fill="#9D174D")
    draw.rectangle([s(x0 + 48), s(water_y - 38), s(x0 + 62), s(water_y)], fill="#831843")

    sx0 = x1 - 78
    for dx in (0, 21, 42):
        draw.rectangle([s(sx0 + dx), s(water_y - 24), s(sx0 + dx + 12), s(water_y)], fill="#0F766E")
    draw.polygon([(s(sx0 - 6), s(water_y - 24)), (s(sx0 + 60), s(water_y - 24)), (s(sx0 + 65), s(water_y - 30)), (s(sx0 - 2), s(water_y - 30))], fill="#115E59")

    cy = y0 + 37
    lx, rx = x0 + 104, x1 - 122
    draw.line([s(lx + 16), s(cy - 6), s(rx - 16), s(cy - 6)], fill=GOLD, width=s(3.8))
    draw.polygon([(s(rx - 13), s(cy - 6)), (s(rx - 22), s(cy - 12)), (s(rx - 22), s(cy))], fill=GOLD)
    draw.line([s(lx + 21), s(cy + 7), s(rx - 16), s(cy + 7)], fill="#1E293B", width=s(3.8))
    draw.polygon([(s(lx + 13), s(cy + 7)), (s(lx + 22), s(cy + 1)), (s(lx + 22), s(cy + 13))], fill="#1E293B")

    draw.ellipse([s(lx - 18), s(cy - 18), s(lx + 18), s(cy + 18)], fill="#9D174D", outline=GOLD_LIGHT, width=s(2.4))
    draw_centered_text(draw, lx, cy, "¥", load_font(SANS_BLACK, 22.0), "#FFFFFF")
    draw.ellipse([s(rx - 18), s(cy - 18), s(rx + 18), s(cy + 18)], fill="#0F766E", outline=GOLD_LIGHT, width=s(2.4))
    draw_centered_text(draw, rx, cy, "S$", load_font(SANS_BLACK, 18.0), "#FFFFFF")

    draw_plaque(draw, x1 - 7, y0 + 5, "RMB HUB", "#9D174D", font_px=15.0, pad_x=6.0, h=21.0)


def art_ariane6(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float]) -> None:
    x0, y0, x1, y1 = box
    draw.rectangle([s(x0), s(y0), s(x1), s(y1)], fill="#134E4A")
    draw.rectangle([s(x0), s(y1 - 20), s(x1), s(y1)], fill="#0F766E")
    for cx, r in [(x0 + 18, 12), (x0 + 38, 14), (x0 + 144, 13), (x0 + 172, 15), (x0 + 206, 12), (x1 - 24, 14)]:
        draw.chord([s(cx - r), s(y1 - r - 5), s(cx + r), s(y1 + r - 5)], start=180, end=360, fill="#064E3B")
    draw.rectangle([s(x0), s(y1 - 7), s(x1), s(y1)], fill="#042F2E")

    draw.arc([s(x0 + 106), s(y0 - 9), s(x1 - 24), s(y1 + 42)], start=198, end=312, fill="#5EEAD4", width=s(2.2))
    for sx, sy in [(x0 + 138, y0 + 20), (x0 + 168, y0 + 13), (x0 + 196, y0 + 16)]:
        draw.rectangle([s(sx - 4.5), s(sy - 2.5), s(sx + 4.5), s(sy + 2.5)], fill="#FACC15")
        draw.line([s(sx - 10), s(sy), s(sx + 10), s(sy)], fill="#38BDF8", width=s(1.8))

    gx = x0 + 58
    draw.rectangle([s(gx - 7), s(y0 + 12), s(gx + 5), s(y1 - 8)], fill="#334155")
    for gy in range(int(y0 + 17), int(y1 - 10), 10):
        draw.line([s(gx - 7), s(gy), s(gx + 5), s(gy + 6)], fill="#94A3B8", width=s(1.5))

    rx = x0 + 92
    draw.rectangle([s(rx - 6.5), s(y0 + 18), s(rx + 6.5), s(y1 - 9)], fill="#F8FAFC")
    draw.polygon([(s(rx), s(y0 + 5)), (s(rx + 6.5), s(y0 + 18)), (s(rx - 6.5), s(y0 + 18))], fill="#FFFFFF")
    draw.rectangle([s(rx - 6.5), s(y0 + 22), s(rx + 6.5), s(y0 + 29)], fill="#2563EB")
    for bdx in (-11, 11):
        draw.rectangle([s(rx + bdx - 3), s(y0 + 32), s(rx + bdx + 3), s(y1 - 9)], fill="#E2E8F0")
        draw.polygon([(s(rx + bdx), s(y0 + 25)), (s(rx + bdx + 3), s(y0 + 32)), (s(rx + bdx - 3), s(y0 + 32))], fill="#CBD5E1")

    hx, hy = x1 - 44, y1 - 21
    draw.ellipse([s(hx - 15), s(hy - 15), s(hx + 15), s(hy + 15)], fill="#F59E0B", outline="#FFFFFF", width=s(2.3))
    draw.rectangle([s(hx - 5.8), s(hy - 7.5), s(hx - 1.4), s(hy + 7.5)], fill="#0F172A")
    draw.rectangle([s(hx + 1.4), s(hy - 7.5), s(hx + 5.8), s(hy + 7.5)], fill="#0F172A")

    draw_plaque(draw, x1 - 6, y0 + 5, "LAUNCH HOLD", "#0F766E", fg="#FEF08A", font_px=15.0, pad_x=6.0, h=21.0)


def art_australia_econ(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float]) -> None:
    x0, y0, x1, y1 = box
    draw.rectangle([s(x0), s(y0), s(x1), s(y1)], fill="#FEFCE8")
    draw.rectangle([s(x0), s(y1 - 10), s(x1), s(y1)], fill="#FEF08A")

    aus_box = (x0 + 16, y0 + 6, x0 + 124, y1 - 4)
    rings = extract_region_polygons((111.0, 156.0), (-45.0, -9.0))
    if rings:
        for ring in rings:
            pts = [(s(px), s(py)) for px, py in (project_lonlat(lo, la, aus_box, 112.0, 155.0, -44.0, -10.0) for lo, la in ring)]
            if len(pts) >= 3:
                draw.polygon(pts, fill="#B45309", outline="#78350F")

    for sx, sy in [(x0 + 54, y0 + 31), (x0 + 63, y0 + 24), (x0 + 72, y0 + 31), (x0 + 63, y0 + 42)]:
        draw.ellipse([s(sx - 2.1), s(sy - 2.1), s(sx + 2.1), s(sy + 2.1)], fill="#FEF9C3")

    gx0 = x0 + 150
    floor_y = y1 - 9
    draw.line([s(gx0), s(floor_y), s(x1 - 10), s(floor_y)], fill="#047857", width=s(3.0))
    for bx, bh, col in [(gx0 + 10, 36, "#D97706"), (gx0 + 42, 28, "#D97706"), (gx0 + 74, 21, "#92400E"), (gx0 + 106, 15, "#92400E")]:
        draw.rounded_rectangle([s(bx), s(floor_y - bh), s(bx + 22), s(floor_y - 2)], radius=s(3), fill=col)

    draw_plaque(draw, x1 - 7, y0 + 5, "GDP <2%", "#92400E", font_px=15.0, pad_x=6.0, h=21.0)


def art_africa_health(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float]) -> None:
    x0, y0, x1, y1 = box
    draw.rectangle([s(x0), s(y0), s(x1), s(y1)], fill="#ECFDF5")
    draw.polygon([(s(x0), s(y1)), (s(x0), s(y1 - 21)), (s(x0 + 75), s(y1 - 31)), (s(x0 + 170), s(y1 - 18)), (s(x1), s(y1 - 28)), (s(x1), s(y1))], fill="#A7F3D0")
    draw.polygon([(s(x0), s(y1)), (s(x0), s(y1 - 12)), (s(x0 + 120), s(y1 - 19)), (s(x0 + 240), s(y1 - 10)), (s(x1), s(y1 - 16)), (s(x1), s(y1))], fill="#6EE7B7")

    ax = x0 + 42
    draw.rectangle([s(ax - 24), s(y1 - 22), s(ax + 24), s(y1 - 5)], fill="#065F46")
    draw.chord([s(ax - 20), s(y1 - 38), s(ax + 20), s(y1 - 9)], start=180, end=360, fill="#047857")
    draw.rectangle([s(ax + 16), s(y1 - 47), s(ax + 26), s(y1 - 5)], fill="#064E3B")

    scx, scy = x0 + 130, (y0 + y1) / 2
    for r in (27, 21):
        draw.ellipse([s(scx - r), s(scy - r), s(scx + r), s(scy + r)], outline="#10B981", width=s(1.9))
    shield = [(s(scx), s(scy - 18)), (s(scx + 17), s(scy - 11)), (s(scx + 15), s(scy + 5)), (s(scx), s(scy + 18)), (s(scx - 15), s(scy + 5)), (s(scx - 17), s(scy - 11))]
    draw.polygon(shield, fill="#047857", outline="#064E3B")
    draw.rectangle([s(scx - 3.5), s(scy - 9), s(scx + 3.5), s(scy + 9)], fill="#FFFFFF")
    draw.rectangle([s(scx - 9), s(scy - 3.5), s(scx + 9), s(scy + 3.5)], fill="#FFFFFF")

    vx, vy = x0 + 200, (y0 + y1) / 2 + 4
    draw.rounded_rectangle([s(vx - 11), s(vy - 12), s(vx + 11), s(vy + 15)], radius=s(4), fill="#FFFFFF", outline="#047857", width=s(2.0))
    draw.rectangle([s(vx - 8), s(vy - 1), s(vx + 8), s(vy + 12)], fill="#10B981")
    draw.rectangle([s(vx - 7), s(vy - 19), s(vx + 7), s(vy - 12)], fill="#0F172A")

    draw_plaque(draw, x1 - 7, y0 + 5, "CPHIA ADDIS", "#065F46", font_px=15.0, pad_x=6.0, h=21.0)


def art_bbc_media(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float]) -> None:
    x0, y0, x1, y1 = box
    draw.rectangle([s(x0), s(y0), s(x1), s(y1)], fill="#EFF6FF")

    bx = x0 + 58
    for r in (14, 23):
        draw.arc([s(bx - r), s(y0 + 3), s(bx + r), s(y0 + 3 + r)], start=205, end=335, fill="#3B82F6", width=s(2.0))
    draw.line([s(bx), s(y0 + 8), s(bx), s(y0 + 24)], fill="#1E293B", width=s(2.4))
    draw.rectangle([s(bx - 36), s(y0 + 32), s(bx + 36), s(y1)], fill="#334155")
    draw.rectangle([s(bx - 25), s(y0 + 23), s(bx + 25), s(y1)], fill="#1E293B")
    for i, ch in enumerate(["B", "B", "C"]):
        ex = bx - 24.5 + i * 16.5
        draw.rectangle([s(ex), s(y0 + 37), s(ex + 14.5), s(y0 + 56)], fill="#0F172A", outline="#FFFFFF", width=s(1.1))
        draw_centered_text(draw, ex + 7.25, y0 + 46.5, ch, load_font(SANS_BLACK, 15.0), "#FFFFFF")

    cx0, cx1 = x0 + 124, x1 - 14
    mid_y = y0 + 43
    pts = [(s(cx0), s(y0 + 23)), (s(cx0 + 44), s(y0 + 29)), (s(cx0 + 88), s(mid_y)), (s(cx1 - 36), s(y1 - 9))]
    draw.polygon(pts + [(s(cx1 - 36), s(y1)), (s(cx0), s(y1))], fill="#FEE2E2")
    for dx in range(int(cx0), int(cx1 - 34), 10):
        draw.line([s(dx), s(mid_y), s(dx + 6), s(mid_y)], fill="#64748B", width=s(1.7))
    draw.line(pts, fill="#DC2626", width=s(4.0))
    draw.polygon([(s(cx1 - 28), s(y1 - 6)), (s(cx1 - 43), s(y1 - 7)), (s(cx1 - 35), s(y1 - 18))], fill="#DC2626")

    draw_plaque(draw, x1 - 7, y0 + 5, "<50% FEE", "#1D4ED8", font_px=15.0, pad_x=6.0, h=21.0)


def art_india_nepal(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float]) -> None:
    x0, y0, x1, y1 = box
    draw.rectangle([s(x0), s(y0), s(x1), s(y1)], fill="#E0F2FE")

    peaks = [
        ([(x0 + 8, y1), (x0 + 70, y0 + 9), (x0 + 132, y1)], "#64748B", [(x0 + 52, y0 + 28), (x0 + 70, y0 + 9), (x0 + 88, y0 + 28)]),
        ([(x0 + 96, y1), (x0 + 166, y0 + 5), (x0 + 236, y1)], "#475569", [(x0 + 144, y0 + 26), (x0 + 166, y0 + 5), (x0 + 188, y0 + 26)]),
        ([(x0 + 196, y1), (x0 + 260, y0 + 14), (x1, y1)], "#64748B", [(x0 + 242, y0 + 32), (x0 + 260, y0 + 14), (x0 + 278, y0 + 32)]),
    ]
    for body, col, cap in peaks:
        draw.polygon([(s(px), s(py)) for px, py in body], fill=col)
        draw.polygon([(s(px), s(py)) for px, py in cap], fill="#FFFFFF")

    dx0, dx1 = x0 + 104, x0 + 188
    draw.polygon([(s(dx0), s(y1 - 27)), (s(dx1), s(y1 - 27)), (s(dx1 + 8), s(y1)), (s(dx0 - 8), s(y1))], fill="#CBD5E1", outline="#334155")
    for wx in (dx0 + 14, dx0 + 35, dx0 + 56):
        draw.rectangle([s(wx), s(y1 - 21), s(wx + 13), s(y1)], fill="#0284C7")
        draw.line([s(wx + 6.5), s(y1 - 19), s(wx + 6.5), s(y1 - 2)], fill="#BAE6FD", width=s(2.4))

    for px in (x0 + 38, x1 - 44):
        draw.line([s(px), s(y0 + 17), s(px - 9), s(y1 - 3)], fill="#9D174D", width=s(2.4))
        draw.line([s(px), s(y0 + 17), s(px + 9), s(y1 - 3)], fill="#9D174D", width=s(2.4))
        draw.line([s(px - 13), s(y0 + 26), s(px + 13), s(y0 + 26)], fill="#9D174D", width=s(2.4))
    draw.arc([s(x0 + 38), s(y0 + 13), s(x1 - 44), s(y0 + 42)], start=0, end=180, fill="#F59E0B", width=s(2.6))

    draw_plaque(draw, x1 - 7, y0 + 5, "HYDRO PACT", "#9D174D", font_px=15.0, pad_x=6.0, h=21.0)


def draw_gallery_card(
    draw: ImageDraw.ImageDraw,
    rect: tuple[float, float, float, float],
    tag: str,
    color: str,
    art_fn: Any,
    headline_lines: list[str],
    audit_boxes: list[tuple[str, tuple[float, float, float, float]]],
) -> None:
    x0, y0, x1, y1 = rect
    rounded_rect(draw, rect, radius=8, fill=CARD_BG, outline=HAIRLINE, width=1.0)

    strip_h = 23.0
    top_rounded_strip(draw, x0 + 1, y0 + 1, x1 - 1, y0 + strip_h, radius=7, fill=color)
    tag_font = load_font(SANS_BLACK, 15.0)
    draw_left_text(draw, x0 + 10, y0 + strip_h / 2, tag, tag_font, "#FFFFFF")

    art_box = (x0 + 2, y0 + strip_h, x1 - 2, y0 + strip_h + 68)
    art_fn(draw, art_box)
    draw.line([s(x0 + 1), s(art_box[3]), s(x1 - 1), s(art_box[3])], fill="#E8E1D1", width=s(1.0))

    # Giant 21.5px Lato-Black sans-serif headline (zero 1-word widows!)
    hl_font = load_font(SANS_BLACK, 21.5)
    mid_y = (art_box[3] + y1) / 2
    ys = [mid_y - 12.5, mid_y + 12.5] if len(headline_lines) == 2 else [mid_y]
    for line, ly in zip(headline_lines, ys):
        assert len(line.split()) >= 2, f"Orphan 1-word widow line: '{line}'"
        b = draw_centered_text(draw, (x0 + x1) / 2, ly, line, hl_font, INK)
        audit_boxes.append((f"card_hl:{line}", b))
        assert b[0] >= x0 + 5 and b[2] <= x1 - 5, f"Card headline clipped: '{line}' ({b[0]:.1f}..{b[2]:.1f} vs {x0+5}..{x1-5})"


def draw_global_dispatch_band(
    draw: ImageDraw.ImageDraw,
    rect: tuple[float, float, float, float],
    audit_boxes: list[tuple[str, tuple[float, float, float, float]]],
) -> None:
    """Airy dark-navy 2x6 Global Dispatch Band (12 high-impact pure Monday 23 Nov stories)."""
    x0, y0, x1, y1 = rect
    rounded_rect(draw, rect, radius=8, fill=NAVY_DARK)
    top_rounded_strip(draw, x0, y0, x1, y0 + 4, radius=7, fill=GOLD)

    left_items = [
        ("BELGIUM", REGION_COLORS["EUROPE"], "National strike halts Belgian airspace"),
        ("GULF OIL", REGION_COLORS["MIDDLE_EAST"], "Saudi & Japan add 16M bbl oil storage"),
        ("GAZA", REGION_COLORS["MIDDLE_EAST"], "Oxfam warns Gaza faces toxic crisis"),
        ("COLOMBIA", REGION_COLORS["S_AMERICA"], "Chocó malaria jumps 46% post-quake"),
        ("CANADA", REGION_COLORS["AMERICAS"], "Bombardier union backs strike 97.8%"),
        ("EUROPE", REGION_COLORS["EUROPE"], "Living-cost protests sweep EU cities"),
    ]
    right_items = [
        ("VANUATU", REGION_COLORS["OCEANIA"], "M6.5 deep quake strikes off Vanuatu"),
        ("AVIATION", REGION_COLORS["ASIA"], "XPENG ARIDGE flies electric tiltrotor"),
        ("AFRICA", REGION_COLORS["AFRICA"], "S. Africa & Zambia link live customs"),
        ("WATER", REGION_COLORS["AFRICA"], "Africa Water Summit opens in Durban"),
        ("M. EAST", REGION_COLORS["MIDDLE_EAST"], "Egypt & Iraq hold Cairo security talks"),
        ("SPORT", REGION_COLORS["OCEANIA"], "New Zealand holds India to Test draw"),
    ]

    pill_font = load_font(SANS_BLACK, 15.0)
    text_font = load_font(SANS_BOLD, 17.5)

    mid_x = (x0 + x1) / 2
    draw.line([s(mid_x), s(y0 + 10), s(mid_x), s(y1 - 8)], fill="#243B53", width=s(1.2))

    top_pad = 8.0
    row_h = (y1 - y0 - top_pad - 5.0) / 6.0  # ~30.8px per airy row
    pill_w = 96.0
    pill_h = 23.0

    for col_idx, col_items in enumerate((left_items, right_items)):
        cx0 = x0 + 10 if col_idx == 0 else mid_x + 10
        col_limit = (mid_x - 8) if col_idx == 0 else (x1 - 10)
        for row_idx, (badge, bcol, headline) in enumerate(col_items):
            ry_top = y0 + top_pad + row_idx * row_h
            cy = ry_top + row_h / 2
            if row_idx > 0:
                draw.line([s(cx0), s(ry_top), s(col_limit), s(ry_top)], fill="#1B3046", width=s(0.9))
            brect = (cx0, cy - pill_h / 2, cx0 + pill_w, cy + pill_h / 2)
            rounded_rect(draw, brect, radius=4.5, fill=bcol)
            draw_centered_text(draw, cx0 + pill_w / 2, cy, badge, pill_font, "#FFFFFF")

            tb = draw_left_text(draw, cx0 + pill_w + 9, cy, headline, text_font, "#FFFFFF")
            audit_boxes.append((f"wire:{headline}", tb))
            assert tb[2] <= col_limit, f"Dispatch clipped: '{headline}' right={tb[2]:.1f} > {col_limit:.1f}"


def audit_overlaps(boxes: list[tuple[str, tuple[float, float, float, float]]]) -> list[str]:
    issues: list[str] = []
    for i in range(len(boxes)):
        name_a, (ax0, ay0, ax1, ay1) = boxes[i]
        if ax0 < 0 or ay0 < 0 or ax1 > WIDTH or ay1 > HEIGHT:
            issues.append(f"OUT_OF_BOUNDS {name_a}: {(ax0, ay0, ax1, ay1)}")
        for j in range(i + 1, len(boxes)):
            name_b, (bx0, by0, bx1, by1) = boxes[j]
            if ax0 < bx1 and ax1 > bx0 and ay0 < by1 and ay1 > by0:
                issues.append(f"OVERLAP {name_a} vs {name_b}")
    return issues


def save_compact_rgb_png(img: Image.Image, path: Path) -> int:
    rgb = img.convert("RGB")
    arr = np.asarray(rgb, dtype=np.uint8)
    h, w, _ = arr.shape
    raw = arr.reshape(h, w * 3)

    def apply_filter(cur: np.ndarray, prev: np.ndarray, mode: int) -> np.ndarray:
        if mode == 0:
            return cur
        if mode == 1:
            left = np.concatenate([np.zeros(3, dtype=np.uint8), cur[:-3]])
            return ((cur.astype(np.int16) - left.astype(np.int16)) & 0xFF).astype(np.uint8)
        if mode == 2:
            return ((cur.astype(np.int16) - prev.astype(np.int16)) & 0xFF).astype(np.uint8)
        if mode == 3:
            left = np.concatenate([np.zeros(3, dtype=np.uint8), cur[:-3]]).astype(np.int16)
            return ((cur.astype(np.int16) - ((left + prev.astype(np.int16)) >> 1)) & 0xFF).astype(np.uint8)
        a = np.concatenate([np.zeros(3, dtype=np.uint8), cur[:-3]]).astype(np.int16)
        b = prev.astype(np.int16)
        c = np.concatenate([np.zeros(3, dtype=np.uint8), prev[:-3]]).astype(np.int16)
        p = a + b - c
        pa, pb, pc = np.abs(p - a), np.abs(p - b), np.abs(p - c)
        pr = np.where((pa <= pb) & (pa <= pc), a, np.where(pb <= pc, b, c))
        return ((cur.astype(np.int16) - pr) & 0xFF).astype(np.uint8)

    out = bytearray()
    prev = np.zeros(raw.shape[1], dtype=np.uint8)
    for y in range(h):
        cur = raw[y]
        best_m = 0
        best_f = cur
        best_score = 10**18
        for m in range(5):
            filt = apply_filter(cur, prev, m)
            fi = filt.astype(np.int16)
            score = int(np.minimum(fi, 256 - fi).sum())
            if score < best_score:
                best_m, best_f, best_score = m, filt, score
        out.append(best_m)
        out.extend(best_f.tobytes())
        prev = cur

    compressed = zlib.compress(bytes(out), level=9)

    def make_chunk(kind: bytes, payload: bytes) -> bytes:
        crc = zlib.crc32(kind + payload) & 0xFFFFFFFF
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    png_bytes = b"\x89PNG\r\n\x1a\n" + make_chunk(b"IHDR", ihdr) + make_chunk(b"IDAT", compressed) + make_chunk(b"IEND", b"")
    path.write_bytes(png_bytes)
    return len(png_bytes)


def render() -> None:
    img = Image.new("RGB", (CW, CH), PAPER)
    draw = ImageDraw.Draw(img)
    audit_boxes: list[tuple[str, tuple[float, float, float, float]]] = []

    # 1. TOP MASTHEAD (0..68px)
    draw.rectangle([0, 0, CW, s(22)], fill=NAVY_DARK)
    ribbon_font = load_font(SANS_BLACK, 15.0)
    draw_centered_text(draw, WIDTH / 2, 11.0, "WORLD NEWS ATLAS   ·   7 REGIONS   ·   23 STORIES", ribbon_font, GOLD_LIGHT)

    date_font = load_font(SERIF_BOLD, 44.0)
    date_box = draw_centered_text(draw, WIDTH / 2, 45, "Monday 23 November 2026", date_font, INK)
    audit_boxes.append(("masthead:date", date_box))

    draw.rectangle([s(12), s(67), s(WIDTH - 12), s(69)], fill=NAVY_DARK)
    draw.rectangle([s(12), s(70), s(WIDTH - 12), s(71.5)], fill=GOLD)

    # 2. UPPER VISUAL HERO (76..346px, 270px tall)
    draw_world_map(draw, (12, 76, 594, 346), audit_boxes)

    draw_lead_card(
        draw,
        (604, 76, 1012, 207),
        "LEAD 1  ·  GLOBAL · MARKETS",
        REGION_COLORS["GLOBAL"],
        ["AI Tech Rout Hits;", "Asia Launches Rescue"],
        ["China 16-mo low · Taiwan curbs", "Korea readies $8B rescue fund"],
        draw_lead1_art,
        audit_boxes,
    )
    draw_lead_card(
        draw,
        (604, 215, 1012, 346),
        "LEAD 2  ·  MIDDLE EAST · OIL",
        REGION_COLORS["MIDDLE_EAST"],
        ["Iran Vows Response", "to U.S. Oil Blockade"],
        ["Tehran vows all tools; U.S.", "warns blockade-running ships"],
        draw_lead2_art,
        audit_boxes,
    )

    # 3. MIDDLE ILLUSTRATED GALLERY: 3x3 GIANT 326px PANORAMIC CARDS (352..814px, 462px tall)
    cards = [
        ("EUROPE · ENERGY", REGION_COLORS["EUROPE"], art_eu_gas, ["Europe Gas Jumps 6%", "to €93 on Cold Snap"]),
        ("AFRICA · OIL", REGION_COLORS["AFRICA"], art_libya_oil, ["Libya Valve Closure", "Cuts 350k bpd Oil"]),
        ("AMERICAS · ECONOMY", REGION_COLORS["AMERICAS"], art_us_fed, ["Bessent Warns Fed", "Over Hawkish Rates"]),
        ("ASIA · FINANCE", REGION_COLORS["ASIA"], art_sg_china_rmb, ["Singapore & China", "Expand RMB Liquidity"]),
        ("S. AMERICA · SPACE", REGION_COLORS["S_AMERICA"], art_ariane6, ["Ariane 6 Launch", "Halted at Kourou"]),
        ("OCEANIA · ECONOMY", REGION_COLORS["OCEANIA"], art_australia_econ, ["Australia Sees Slow", "Growth, No Recession"]),
        ("AFRICA · HEALTH", REGION_COLORS["AFRICA"], art_africa_health, ["Africa Public Health", "Summit Opens in Addis"]),
        ("EUROPE · MEDIA", REGION_COLORS["EUROPE"], art_bbc_media, ["Report Warns BBC", "Fee Faces Decline"]),
        ("S. ASIA · DIPLOMACY", REGION_COLORS["ASIA"], art_india_nepal, ["India & Nepal Sign", "Hydropower Pacts"]),
    ]

    col_xs = [(12, 337), (349, 675), (687, 1012)]
    row_ys = [(352, 500), (509, 657), (666, 814)]
    for idx, (tag, color, art_fn, lines) in enumerate(cards):
        r = idx // 3
        c = idx % 3
        cx0, cx1 = col_xs[c]
        ry0, ry1 = row_ys[r]
        draw_gallery_card(draw, (cx0, ry0, cx1, ry1), tag, color, art_fn, lines, audit_boxes)

    # 4. BOTTOM AIRY DARK-NAVY 2x6 GLOBAL DISPATCH BAND (820..1018px, 198px tall)
    draw_global_dispatch_band(draw, (12, 820, 1012, 1018), audit_boxes)

    issues = audit_overlaps(audit_boxes)
    if issues:
        raise RuntimeError("Layout audit failed:\n" + "\n".join(issues))

    final = img.resize((WIDTH, HEIGHT), Image.Resampling.BOX).convert("RGB")
    size_bytes = save_compact_rgb_png(final, OUT_PNG)

    preview = final.resize((300, 300), Image.Resampling.LANCZOS)
    preview.save("/tmp/news23_v3_300px.png", format="PNG", optimize=True)

    print(
        f"Rendered v3b (23 stories) {OUT_PNG} ({WIDTH}x{HEIGHT} 8-bit RGB, {size_bytes:,} bytes), "
        f"MIN_FONT_PX={MIN_FONT_PX}, layout audit: 0 issues ({len(audit_boxes)} boxes checked)."
    )


if __name__ == "__main__":
    render()
