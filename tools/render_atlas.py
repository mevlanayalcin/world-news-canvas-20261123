#!/usr/bin/env python3
"""Render the 1024x1024 World News Atlas for Monday 23 November 2026.

Editorial broadsheet architecture with strict >= 15.0px font floor everywhere,
2x supersampled vector art, soft archival hairline rules, giant 18.5px map
callouts, 23.5px hero leads, 22px 3x3 card headlines, and 17.5px dark-navy wire.
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
    legend_h = 28.0
    map_box = (px0, py0, px1, py1 - legend_h)
    mx0, my0, mx1, my1 = map_box

    # Soft hairline editorial frame + ocean fill
    rounded_rect(draw, panel, radius=8, fill=OCEAN, outline=HAIRLINE, width=1.0)

    # Subtle graticule lines
    for lon in range(-150, 180, 30):
        gx, _ = project_lonlat(lon, 0, map_box)
        if mx0 + 4 < gx < mx1 - 4:
            draw.line([s(gx), s(my0 + 2), s(gx), s(my1)], fill=OCEAN_GRID, width=1)
    for lat in (-30, 0, 30, 60):
        _, gy = project_lonlat(0, lat, map_box)
        if my0 + 4 < gy < my1 - 4:
            draw.line([s(mx0 + 2), s(gy), s(mx1 - 2), s(gy)], fill=OCEAN_GRID, width=1)

    # Natural Earth 110m warm-parchment land polygons
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

    # Clean map badge top-left (15px bold)
    title_font = load_font(SANS_BLACK, 15.0)
    t_rect = (mx0 + 8, my0 + 7, mx0 + 178, my0 + 32)
    rounded_rect(draw, t_rect, radius=5, fill=NAVY_DARK)
    draw_centered_text(draw, (t_rect[0] + t_rect[2]) / 2, (t_rect[1] + t_rect[3]) / 2, "WORLD HOTSPOTS", title_font, "#FFFFFF")

    # Secondary crisp pins for other featured stories (no cluttered labels!)
    minor_pins = [
        (38.7, 9.0, REGION_COLORS["AFRICA"]),    # Addis Ababa
        (103.8, 1.3, REGION_COLORS["ASIA"]),     # Singapore
        (77.2, 28.6, REGION_COLORS["ASIA"]),     # New Delhi / Nepal
        (174.8, -41.3, REGION_COLORS["OCEANIA"]),# Wellington NZ
    ]
    for lon, lat, col in minor_pins:
        px, py = project_lonlat(lon, lat, map_box)
        draw.ellipse([s(px - 5.2), s(py - 5.2), s(px + 5.2), s(py + 5.2)], fill="#FFFFFF", outline=INK, width=s(1.0))
        draw.ellipse([s(px - 3.3), s(py - 3.3), s(px + 3.3), s(py + 3.3)], fill=col)

    # 6 GIANT 18.5px BOLD 1-2 WORD CALLOUT LABELS in wide-open ocean, ZERO crisscrossing lines!
    pill_font = load_font(SANS_BLACK, 18.5)
    callouts = [
        # (label, lon, lat, pill_x, pill_y, color)
        ("U.S. FED", -77.0, 38.9, mx0 + 10, my0 + 114, REGION_COLORS["AMERICAS"]),
        ("GUIANA", -52.7, 5.2, mx0 + 16, my0 + 216, REGION_COLORS["S_AMERICA"]),
        ("EU GAS", 4.9, 52.3, mx0 + 196, my0 + 10, REGION_COLORS["EUROPE"]),
        ("LIBYA", 12.2, 26.5, mx0 + 214, my0 + 190, REGION_COLORS["AFRICA"]),
        ("#2 IRAN", 56.3, 26.5, mx0 + 356, my0 + 158, REGION_COLORS["MIDDLE_EAST"]),
        ("#1 ASIA", 125.0, 34.5, mx0 + 464, my0 + 20, REGION_COLORS["GLOBAL"]),
        ("AUSTRALIA", 149.1, -35.3, mx0 + 440, my0 + 236, REGION_COLORS["OCEANIA"]),
    ]

    computed = []
    for label, lon, lat, px, py, color in callouts:
        tw, _ = text_size(draw, label, pill_font)
        pw = tw + 18
        ph = 28.0
        px = max(mx0 + 6, min(mx1 - pw - 6, px))
        py = max(my0 + 6, min(my1 - ph - 6, py))
        pin_x, pin_y = project_lonlat(lon, lat, map_box)
        computed.append((label, pin_x, pin_y, px, py, pw, ph, color))

    # Short direct anchor stems (zero crossing)
    for label, pin_x, pin_y, px, py, pw, ph, color in computed:
        cx = max(px + 8, min(px + pw - 8, pin_x))
        cy = max(py + 6, min(py + ph - 6, pin_y))
        draw.line([s(pin_x), s(pin_y), s(cx), s(cy)], fill="#FFFFFF", width=s(3.4))
        draw.line([s(pin_x), s(pin_y), s(cx), s(cy)], fill=color, width=s(1.8))

    # High-contrast hotspot pins
    for label, pin_x, pin_y, px, py, pw, ph, color in computed:
        draw.ellipse([s(pin_x - 7.0), s(pin_y - 7.0), s(pin_x + 7.0), s(pin_y + 7.0)], fill="#FFFFFF", outline=INK, width=s(1.2))
        draw.ellipse([s(pin_x - 4.4), s(pin_y - 4.4), s(pin_x + 4.4), s(pin_y + 4.4)], fill=color)

    # Crisp 18.5px pill callouts
    for label, pin_x, pin_y, px, py, pw, ph, color in computed:
        rect = (px, py, px + pw, py + ph)
        rounded_rect(draw, (px + 1.5, py + 1.5, px + pw + 1.5, py + ph + 1.5), radius=12, fill="#B5C8D8")
        rounded_rect(draw, rect, radius=12, fill="#FFFFFF", outline=color, width=2.2)
        draw_centered_text(draw, px + pw / 2, py + ph / 2, label, pill_font, INK)
        audit_boxes.append((f"map_pill:{label}", rect))

    # Bottom clean 15px bold region legend strip
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
        draw.ellipse([s(cur_x), s(cy - 4.8), s(cur_x + 9.6), s(cy + 4.8)], fill=col)
        draw_left_text(draw, cur_x + 12.5, cy, lbl, leg_font, INK)
        cur_x += iw + gap


def draw_lead1_art(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float]) -> None:
    """Global AI Tech Rout + Asia Market Rescue Shield."""
    x0, y0, x1, y1 = box
    h = y1 - y0
    rounded_rect(draw, box, radius=6, fill="#FEF2F2", outline="#FECACA", width=1.0)

    for i in range(1, 4):
        gy = y0 + h * i / 4
        draw.line([s(x0 + 6), s(gy), s(x1 - 6), s(gy)], fill="#FDE2E2", width=s(1))

    bars = [
        (x0 + 12, y0 + 14, 9, 20, "#DC2626"),
        (x0 + 27, y0 + 24, 9, 24, "#DC2626"),
        (x0 + 42, y0 + 38, 9, 26, "#B91C1C"),
        (x0 + 57, y0 + 54, 9, 30, "#991B1B"),
    ]
    for bx, by, bw, bh, col in bars:
        draw.line([s(bx + bw / 2), s(by - 5), s(bx + bw / 2), s(by + bh + 5)], fill=col, width=s(2))
        draw.rectangle([s(bx), s(by), s(bx + bw), s(by + bh)], fill=col)

    pts = [
        (s(x0 + 10), s(y0 + 16)),
        (s(x0 + 40), s(y0 + 38)),
        (s(x0 + 50), s(y0 + 32)),
        (s(x0 + 72), s(y0 + 80)),
    ]
    draw.line(pts, fill="#991B1B", width=s(4.0))
    draw.polygon(
        [(s(x0 + 75), s(y0 + 86)), (s(x0 + 62), s(y0 + 79)), (s(x0 + 76), s(y0 + 70))],
        fill="#991B1B",
    )

    scx, scy = x1 - 26, y1 - 30
    shield = [
        (s(scx), s(scy - 21)),
        (s(scx + 18), s(scy - 14)),
        (s(scx + 16), s(scy + 6)),
        (s(scx), s(scy + 20)),
        (s(scx - 16), s(scy + 6)),
        (s(scx - 18), s(scy - 14)),
    ]
    draw.polygon(shield, fill="#0D1B2A")
    draw.line(shield + [shield[0]], fill="#C89B3C", width=s(2.4))
    draw.line(
        [(s(scx - 7), s(scy + 1)), (s(scx - 1.5), s(scy + 6.5)), (s(scx + 8.5), s(scy - 6))],
        fill="#FACC15",
        width=s(3.2),
    )

    tag_font = load_font(SANS_BLACK, 15.0)
    rounded_rect(draw, (x1 - 52, y0 + 7, x1 - 6, y0 + 29), radius=5, fill="#B91C1C")
    draw_centered_text(draw, x1 - 29, y0 + 18, "-10%", tag_font, "#FFFFFF")


def draw_lead2_art(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float]) -> None:
    """Iran Oil Blockade in Strait of Hormuz."""
    x0, y0, x1, y1 = box
    h = y1 - y0
    rounded_rect(draw, box, radius=6, fill="#FFF4E6", outline="#FED7AA", width=1.0)

    draw.ellipse([s(x0 + 8), s(y0 + 8), s(x0 + 32), s(y0 + 32)], fill="#FDBA74")

    sea_y = y0 + h * 0.56
    rounded_rect(draw, (x0 + 2, sea_y, x1 - 2, y1 - 2), radius=5, fill="#1E3A5F")
    draw.rectangle([s(x0 + 2), s(sea_y), s(x1 - 2), s(sea_y + 10)], fill="#1E3A5F")

    for wy, wx0, wx1 in [(sea_y + 15, x0 + 9, x0 + 40), (sea_y + 27, x0 + 44, x0 + 96), (sea_y + 38, x0 + 14, x0 + 58)]:
        draw.line([s(wx0), s(wy), s(wx1), s(wy)], fill="#60A5FA", width=s(2.0))

    hull = [
        (s(x0 + 10), s(sea_y + 4)),
        (s(x0 + 66), s(sea_y + 4)),
        (s(x0 + 75), s(sea_y - 11)),
        (s(x0 + 12), s(sea_y - 11)),
    ]
    draw.polygon(hull, fill="#0F172A")
    draw.rectangle([s(x0 + 14), s(sea_y - 15), s(x0 + 66), s(sea_y - 10)], fill="#DC2626")
    draw.rectangle([s(x0 + 18), s(sea_y - 29), s(x0 + 32), s(sea_y - 15)], fill="#F8FAFC", outline="#0F172A", width=s(1.2))
    draw.rectangle([s(x0 + 22), s(sea_y - 36), s(x0 + 28), s(sea_y - 29)], fill="#C2410C")
    for tx in (38, 48, 58):
        draw.rounded_rectangle([s(x0 + tx), s(sea_y - 20), s(x0 + tx + 7), s(sea_y - 13)], radius=s(2), fill="#475569")

    bcx, bcy = x1 - 22, sea_y - 18
    draw.arc([s(bcx - 19), s(bcy - 19), s(bcx + 19), s(bcy + 19)], start=110, end=250, fill="#DC2626", width=s(4.0))
    draw.ellipse([s(bcx - 12.5), s(bcy - 12.5), s(bcx + 12.5), s(bcy + 12.5)], fill="#DC2626", outline="#FFFFFF", width=s(2))
    draw.rectangle([s(bcx - 6.5), s(bcy - 2.5), s(bcx + 6.5), s(bcy + 2.5)], fill="#FFFFFF")


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
    strip_h = 26.0
    top_rounded_strip(draw, x0 + 1, y0 + 1, x1 - 1, y0 + strip_h, radius=7, fill=color)
    tag_font = load_font(SANS_BLACK, 15.0)
    draw_left_text(draw, x0 + 10, y0 + strip_h / 2, tag, tag_font, "#FFFFFF")

    art_box = (x0 + 8, y0 + strip_h + 6, x0 + 116, y1 - 8)
    art_fn(draw, art_box)

    tx0 = x0 + 126
    hl_font = load_font(SERIF_BOLD, 23.5)
    sub_font = load_font(SANS_BOLD, 15.5)
    cur_y = y0 + strip_h + 23
    for line in headline_lines:
        b = draw_left_text(draw, tx0, cur_y, line, hl_font, INK)
        audit_boxes.append((f"lead_hl:{line}", b))
        assert b[2] <= x1 - 6, f"Lead headline clipped: '{line}' right={b[2]:.1f} > {x1-6}"
        cur_y += 28
    cur_y += 5
    for sline in sub_lines:
        b = draw_left_text(draw, tx0, cur_y, sline, sub_font, INK_MUTED)
        audit_boxes.append((f"lead_sub:{sline}", b))
        assert b[2] <= x1 - 6, f"Lead sub clipped: '{sline}' right={b[2]:.1f} > {x1-6}"
        cur_y += 21


# ---------- 9 BESPOKE GALLERY VECTOR ILLUSTRATIONS (322 x 80px) ----------

def art_eu_gas(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float]) -> None:
    x0, y0, x1, y1 = box
    mid = (x0 + x1) / 2 - 22
    draw.rectangle([s(x0), s(y0), s(mid), s(y1)], fill="#DBEAFE")
    draw.rectangle([s(mid), s(y0), s(x1), s(y1)], fill="#FEF3C7")

    cx, cy, r = x0 + 50, (y0 + y1) / 2, 23
    for deg in range(0, 360, 60):
        rad = math.radians(deg)
        ex, ey = cx + math.cos(rad) * r, cy + math.sin(rad) * r
        draw.line([s(cx), s(cy), s(ex), s(ey)], fill="#1D4ED8", width=s(3.0))
        bx, by = cx + math.cos(rad) * (r * 0.62), cy + math.sin(rad) * (r * 0.62)
        for a_off in (-42, 42):
            ar = rad + math.radians(a_off)
            draw.line([s(bx), s(by), s(bx + math.cos(ar) * 8), s(by + math.sin(ar) * 8)], fill="#1D4ED8", width=s(2.3))
    draw.ellipse([s(cx - 4.5), s(cy - 4.5), s(cx + 4.5), s(cy + 4.5)], fill="#FFFFFF", outline="#1D4ED8", width=s(2))

    for wy in (y0 + 25, y0 + 40, y0 + 55):
        draw.line([s(x0 + 86), s(wy), s(mid + 6), s(wy)], fill="#3B82F6", width=s(2.6))

    fx, fy = mid + 34, y1 - 11
    outer_flame = [
        (s(fx), s(y0 + 11)),
        (s(fx + 19), s(y0 + 37)),
        (s(fx + 17), s(fy - 4)),
        (s(fx), s(fy + 2)),
        (s(fx - 17), s(fy - 4)),
        (s(fx - 19), s(y0 + 37)),
    ]
    draw.polygon(outer_flame, fill="#EA580C")
    inner_flame = [
        (s(fx), s(y0 + 29)),
        (s(fx + 9.5), s(y0 + 47)),
        (s(fx + 8), s(fy - 4)),
        (s(fx), s(fy - 1)),
        (s(fx - 8), s(fy - 4)),
        (s(fx - 9.5), s(y0 + 47)),
    ]
    draw.polygon(inner_flame, fill="#FACC15")

    px0 = mid + 70
    draw.line(
        [(s(px0), s(y0 + 44)), (s(px0 + 22), s(y0 + 36)), (s(px0 + 40), s(y0 + 38)), (s(px0 + 68), s(y0 + 13))],
        fill="#DC2626",
        width=s(4.0),
    )
    draw.polygon([(s(px0 + 73), s(y0 + 8)), (s(px0 + 58), s(y0 + 12)), (s(px0 + 70), s(y0 + 24))], fill="#DC2626")

    bfont = load_font(SANS_BLACK, 15.0)
    rounded_rect(draw, (x1 - 84, y1 - 28, x1 - 8, y1 - 5), radius=5, fill="#B91C1C")
    draw_centered_text(draw, x1 - 46, y1 - 16.5, "+6% €93", bfont, "#FFFFFF")


def art_libya_oil(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float]) -> None:
    x0, y0, x1, y1 = box
    draw.rectangle([s(x0), s(y0), s(x1), s(y1)], fill="#FEF3C7")
    draw.polygon(
        [(s(x0), s(y1)), (s(x0), s(y1 - 22)), (s(x0 + 95), s(y1 - 31)), (s(x0 + 210), s(y1 - 19)), (s(x1), s(y1 - 27)), (s(x1), s(y1))],
        fill="#E5C992",
    )

    py = y0 + 41
    draw.rectangle([s(x0 + 8), s(py - 9), s(x1 - 104), s(py + 9)], fill="#475569", outline="#1E293B", width=s(1.6))
    draw.line([s(x0 + 10), s(py - 4), s(x1 - 106), s(py - 4)], fill="#94A3B8", width=s(2))
    for fx in (x0 + 54, x0 + 180):
        draw.rectangle([s(fx - 4), s(py - 14), s(fx + 4), s(py + 14)], fill="#334155")
    draw.ellipse([s(x1 - 108), s(py - 9), s(x1 - 100), s(py + 9)], fill="#0F172A", outline="#334155", width=s(1.4))

    vx, vy = x0 + 116, py
    draw.rectangle([s(vx - 6), s(vy - 23), s(vx + 6), s(vy + 14)], fill="#1E293B")
    draw.ellipse([s(vx - 22), s(vy - 22), s(vx + 22), s(vy + 22)], fill="#FEF2F2", outline="#DC2626", width=s(4.6))
    for deg in (0, 60, 120):
        rad = math.radians(deg)
        draw.line(
            [s(vx - math.cos(rad) * 18), s(vy - math.sin(rad) * 18), s(vx + math.cos(rad) * 18), s(vy + math.sin(rad) * 18)],
            fill="#DC2626",
            width=s(3.0),
        )
    draw.ellipse([s(vx - 6), s(vy - 6), s(vx + 6), s(vy + 6)], fill="#991B1B")

    dx, dy = x1 - 94, py + 14
    draw.polygon([(s(dx), s(dy - 9)), (s(dx + 7.5), s(dy + 5)), (s(dx), s(dy + 12)), (s(dx - 7.5), s(dy + 5))], fill="#0F172A")
    draw.ellipse([s(dx - 7.5), s(dy), s(dx + 7.5), s(dy + 14)], fill="#0F172A")

    bfont = load_font(SANS_BLACK, 15.0)
    rounded_rect(draw, (x1 - 88, y0 + 11, x1 - 8, y0 + 36), radius=5, fill="#047857")
    draw_centered_text(draw, x1 - 48, y0 + 23.5, "-350k", bfont, "#FFFFFF")
    rounded_rect(draw, (x1 - 82, y0 + 43, x1 - 12, y0 + 67), radius=5, fill="#1E293B")
    draw_centered_text(draw, x1 - 47, y0 + 55, "bpd cut", load_font(SANS_BOLD, 15.0), "#FDE68A")


def art_us_fed(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float]) -> None:
    x0, y0, x1, y1 = box
    draw.rectangle([s(x0), s(y0), s(x1), s(y1)], fill="#EEF2FF")

    bx0, bx1 = x0 + 18, x0 + 134
    by_base = y1 - 9
    draw.rectangle([s(bx0 - 6), s(by_base - 6), s(bx1 + 6), s(by_base)], fill="#1E3A8A")
    draw.rectangle([s(bx0), s(by_base - 39), s(bx1), s(by_base - 6)], fill="#C7D2FE")
    for cx in (bx0 + 14, bx0 + 42, bx0 + 70, bx0 + 98):
        draw.rectangle([s(cx - 5.5), s(by_base - 39), s(cx + 5.5), s(by_base - 6)], fill="#FFFFFF", outline="#3730A3", width=s(1.4))
    draw.polygon([(s(bx0 - 8), s(by_base - 39)), (s((bx0 + bx1) / 2), s(y0 + 9)), (s(bx1 + 8), s(by_base - 39))], fill="#3730A3")
    draw.ellipse([s((bx0 + bx1) / 2 - 5), s(y0 + 21), s((bx0 + bx1) / 2 + 5), s(y0 + 31)], fill="#FACC15")

    cx = x0 + 208
    draw.rectangle([s(cx - 4), s(y0 + 22), s(cx + 4), s(y1 - 11)], fill="#1E293B")
    draw.rectangle([s(cx - 22), s(y1 - 13), s(cx + 22), s(y1 - 7)], fill="#1E293B")
    draw.line([s(cx - 38), s(y0 + 36), s(cx + 38), s(y0 + 18)], fill="#B91C1C", width=s(4.0))
    draw.line([s(cx - 38), s(y0 + 36), s(cx - 38), s(y0 + 50)], fill="#475569", width=s(1.8))
    draw.chord([s(cx - 52), s(y0 + 40), s(cx - 24), s(y0 + 62)], start=0, end=180, fill="#3730A3")
    draw.line([s(cx + 38), s(y0 + 18), s(cx + 38), s(y0 + 32)], fill="#475569", width=s(1.8))
    draw.chord([s(cx + 24), s(y0 + 22), s(cx + 52), s(y0 + 44)], start=0, end=180, fill="#DC2626")
    draw_centered_text(draw, cx + 47, y0 + 10, "%", load_font(SANS_BLACK, 15.0), "#B91C1C")

    tx, ty = x1 - 36, (y0 + y1) / 2
    tri = [(s(tx), s(ty - 23)), (s(tx + 23), s(ty + 19)), (s(tx - 23), s(ty + 19))]
    draw.polygon(tri, fill="#F59E0B")
    draw.line(tri + [tri[0]], fill="#92400E", width=s(2.4))
    draw_centered_text(draw, tx, ty + 4, "!", load_font(SANS_BLACK, 24.0), "#0F172A")


def art_sg_china_rmb(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float]) -> None:
    x0, y0, x1, y1 = box
    draw.rectangle([s(x0), s(y0), s(x1), s(y1)], fill="#FDF2F8")

    cy = (y0 + y1) / 2
    lx = x0 + 64
    draw.ellipse([s(lx - 29), s(cy - 29), s(lx + 29), s(cy + 29)], fill="#9D174D", outline="#F5D78E", width=s(3.4))
    draw_centered_text(draw, lx, cy, "¥", load_font(SANS_BLACK, 32.0), "#FFFFFF")

    rx = x1 - 64
    draw.ellipse([s(rx - 29), s(cy - 29), s(rx + 29), s(cy + 29)], fill="#0F766E", outline="#F5D78E", width=s(3.4))
    draw_centered_text(draw, rx, cy, "S$", load_font(SANS_BLACK, 26.0), "#FFFFFF")

    ax0, ax1 = lx + 38, rx - 38
    draw.line([s(ax0), s(cy - 10), s(ax1 - 10), s(cy - 10)], fill="#C89B3C", width=s(5))
    draw.polygon([(s(ax1), s(cy - 10)), (s(ax1 - 14), s(cy - 19)), (s(ax1 - 14), s(cy - 1))], fill="#C89B3C")
    draw.line([s(ax0 + 10), s(cy + 10), s(ax1), s(cy + 10)], fill="#1E293B", width=s(5))
    draw.polygon([(s(ax0), s(cy + 10)), (s(ax0 + 14), s(cy + 1)), (s(ax0 + 14), s(cy + 19))], fill="#1E293B")


def art_ariane6(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float]) -> None:
    x0, y0, x1, y1 = box
    draw.rectangle([s(x0), s(y0), s(x1), s(y1)], fill="#134E4A")
    draw.rectangle([s(x0), s(y1 - 22), s(x1), s(y1)], fill="#0F766E")
    draw.rectangle([s(x0), s(y1 - 11), s(x1), s(y1)], fill="#064E3B")

    draw.arc([s(x0 + 120), s(y0 - 14), s(x1 - 10), s(y1 + 52)], start=195, end=330, fill="#5EEAD4", width=s(2.4))
    for sx, sy in [(x0 + 178, y0 + 18), (x0 + 224, y0 + 14), (x0 + 272, y0 + 24)]:
        draw.rectangle([s(sx - 5), s(sy - 3), s(sx + 5), s(sy + 3)], fill="#FACC15")
        draw.line([s(sx - 12), s(sy), s(sx + 12), s(sy)], fill="#38BDF8", width=s(2))

    gx = x0 + 62
    draw.rectangle([s(gx - 8), s(y0 + 15), s(gx + 6), s(y1 - 11)], fill="#334155")
    for gy in range(int(y0 + 21), int(y1 - 13), 12):
        draw.line([s(gx - 8), s(gy), s(gx + 6), s(gy + 8)], fill="#94A3B8", width=s(1.6))

    rx = x0 + 96
    draw.rectangle([s(rx - 7), s(y0 + 21), s(rx + 7), s(y1 - 13)], fill="#F8FAFC")
    draw.polygon([(s(rx), s(y0 + 7)), (s(rx + 7), s(y0 + 21)), (s(rx - 7), s(y0 + 21))], fill="#FFFFFF")
    draw.rectangle([s(rx - 7), s(y0 + 25), s(rx + 7), s(y0 + 33)], fill="#2563EB")
    for bdx in (-12, 12):
        draw.rectangle([s(rx + bdx - 3.5), s(y0 + 37), s(rx + bdx + 3.5), s(y1 - 13)], fill="#E2E8F0")
        draw.polygon([(s(rx + bdx), s(y0 + 29)), (s(rx + bdx + 3.5), s(y0 + 37)), (s(rx + bdx - 3.5), s(y0 + 37))], fill="#CBD5E1")

    hx, hy = x1 - 56, y1 - 29
    draw.ellipse([s(hx - 19), s(hy - 19), s(hx + 19), s(hy + 19)], fill="#F59E0B", outline="#FFFFFF", width=s(2.6))
    draw.rectangle([s(hx - 7.5), s(hy - 9.5), s(hx - 2), s(hy + 9.5)], fill="#0F172A")
    draw.rectangle([s(hx + 2), s(hy - 9.5), s(hx + 7.5), s(hy + 9.5)], fill="#0F172A")


def art_australia_econ(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float]) -> None:
    x0, y0, x1, y1 = box
    draw.rectangle([s(x0), s(y0), s(x1), s(y1)], fill="#FEFCE8")

    aus_box = (x0 + 18, y0 + 7, x0 + 132, y1 - 5)
    rings = extract_region_polygons((111.0, 156.0), (-45.0, -9.0))
    if rings:
        for ring in rings:
            pts = [
                (s(px), s(py))
                for px, py in (project_lonlat(lo, la, aus_box, 112.0, 155.0, -44.0, -10.0) for lo, la in ring)
            ]
            if len(pts) >= 3:
                draw.polygon(pts, fill="#B45309", outline="#78350F")

    gx0 = x0 + 158
    floor_y = y1 - 11
    draw.line([s(gx0), s(floor_y), s(x1 - 12), s(floor_y)], fill="#047857", width=s(3))
    bar_specs = [
        (gx0 + 10, 42, "#D97706"),
        (gx0 + 40, 32, "#D97706"),
        (gx0 + 70, 23, "#92400E"),
        (gx0 + 100, 18, "#92400E"),
    ]
    for bx, bh, col in bar_specs:
        draw.rounded_rectangle([s(bx), s(floor_y - bh), s(bx + 20), s(floor_y - 2)], radius=s(3), fill=col)

    bfont = load_font(SANS_BLACK, 15.0)
    rounded_rect(draw, (x1 - 116, y0 + 7, x1 - 10, y0 + 30), radius=5, fill="#92400E")
    draw_centered_text(draw, x1 - 63, y0 + 18.5, "GDP <2%", bfont, "#FFFFFF")


def art_africa_health(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float]) -> None:
    x0, y0, x1, y1 = box
    draw.rectangle([s(x0), s(y0), s(x1), s(y1)], fill="#ECFDF5")

    draw.polygon(
        [(s(x0), s(y1)), (s(x0), s(y1 - 17)), (s(x0 + 86), s(y1 - 27)), (s(x0 + 188), s(y1 - 15)), (s(x1), s(y1 - 25)), (s(x1), s(y1))],
        fill="#A7F3D0",
    )

    scx, scy = x0 + 86, (y0 + y1) / 2
    for r in (33, 25):
        draw.ellipse([s(scx - r), s(scy - r), s(scx + r), s(scy + r)], outline="#34D399", width=s(2.0))

    shield = [
        (s(scx), s(scy - 21)),
        (s(scx + 19), s(scy - 14)),
        (s(scx + 17), s(scy + 7)),
        (s(scx), s(scy + 21)),
        (s(scx - 17), s(scy + 7)),
        (s(scx - 19), s(scy - 14)),
    ]
    draw.polygon(shield, fill="#047857", outline="#064E3B")
    draw.rectangle([s(scx - 4), s(scy - 10.5), s(scx + 4), s(scy + 10.5)], fill="#FFFFFF")
    draw.rectangle([s(scx - 10.5), s(scy - 4), s(scx + 10.5), s(scy + 4)], fill="#FFFFFF")

    vx, vy = x0 + 196, (y0 + y1) / 2 + 2
    draw.rounded_rectangle([s(vx - 13), s(vy - 15), s(vx + 13), s(vy + 19)], radius=s(5), fill="#FFFFFF", outline="#047857", width=s(2.4))
    draw.rectangle([s(vx - 10), s(vy - 1), s(vx + 10), s(vy + 16)], fill="#10B981")
    draw.rectangle([s(vx - 9), s(vy - 23), s(vx + 9), s(vy - 15)], fill="#0F172A")

    rounded_rect(draw, (x1 - 86, y0 + 10, x1 - 10, y0 + 34), radius=5, fill="#065F46")
    draw_centered_text(draw, x1 - 48, y0 + 22, "CPHIA", load_font(SANS_BLACK, 15.0), "#FFFFFF")


def art_bbc_media(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float]) -> None:
    x0, y0, x1, y1 = box
    draw.rectangle([s(x0), s(y0), s(x1), s(y1)], fill="#EFF6FF")

    tx, ty = x0 + 58, (y0 + y1) / 2 + 4
    for r in (19, 30):
        draw.arc([s(tx - r), s(ty - 31 - r / 2), s(tx + r), s(ty - 31 + r / 2)], start=210, end=330, fill="#3B82F6", width=s(2.2))
    rounded_rect(draw, (tx - 34, ty - 21, tx + 34, ty + 23), radius=6, fill="#1E293B")
    rounded_rect(draw, (tx - 28, ty - 15, tx + 28, ty + 17), radius=4, fill="#DBEAFE")
    for i, ch in enumerate(["B", "B", "C"]):
        bx = tx - 24 + i * 17
        draw.rectangle([s(bx), s(ty - 8), s(bx + 14), s(ty + 10)], fill="#0F172A")
        draw_centered_text(draw, bx + 7, ty + 1, ch, load_font(SANS_BLACK, 15.0), "#FFFFFF")

    cx0, cx1 = x0 + 132, x1 - 18
    mid_y = y0 + 43
    for dx in range(int(cx0), int(cx1 - 44), 10):
        draw.line([s(dx), s(mid_y), s(dx + 6), s(mid_y)], fill="#64748B", width=s(1.8))
    draw_centered_text(draw, cx1 - 21, mid_y, "50%", load_font(SANS_BLACK, 15.0), "#475569")

    pts = [
        (s(cx0), s(y0 + 15)),
        (s(cx0 + 46), s(y0 + 23)),
        (s(cx0 + 88), s(mid_y)),
        (s(cx1 - 46), s(y1 - 15)),
    ]
    draw.line(pts, fill="#DC2626", width=s(4.4))
    draw.polygon([(s(cx1 - 38), s(y1 - 10)), (s(cx1 - 53), s(y1 - 11)), (s(cx1 - 45), s(y1 - 24))], fill="#DC2626")


def art_india_nepal(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float]) -> None:
    x0, y0, x1, y1 = box
    draw.rectangle([s(x0), s(y0), s(x1), s(y1)], fill="#E0F2FE")

    peaks = [
        ([(x0 + 12, y1), (x0 + 78, y0 + 11), (x0 + 144, y1)], "#64748B", [(x0 + 58, y0 + 35), (x0 + 78, y0 + 11), (x0 + 98, y0 + 35)]),
        ([(x0 + 104, y1), (x0 + 186, y0 + 7), (x0 + 266, y1)], "#475569", [(x0 + 162, y0 + 33), (x0 + 186, y0 + 7), (x0 + 210, y0 + 33)]),
        ([(x0 + 210, y1), (x0 + 276, y0 + 17), (x1, y1)], "#64748B", [(x0 + 258, y0 + 37), (x0 + 276, y0 + 17), (x0 + 294, y0 + 37)]),
    ]
    for body, col, cap in peaks:
        draw.polygon([(s(px), s(py)) for px, py in body], fill=col)
        draw.polygon([(s(px), s(py)) for px, py in cap], fill="#FFFFFF")

    dx0, dx1 = x0 + 122, x0 + 202
    draw.polygon([(s(dx0), s(y1 - 30)), (s(dx1), s(y1 - 30)), (s(dx1 + 8), s(y1)), (s(dx0 - 8), s(y1))], fill="#CBD5E1", outline="#334155")
    for wx in (dx0 + 14, dx0 + 34, dx0 + 54):
        draw.rectangle([s(wx), s(y1 - 24), s(wx + 13), s(y1)], fill="#0284C7")
        draw.line([s(wx + 6.5), s(y1 - 22), s(wx + 6.5), s(y1 - 2)], fill="#BAE6FD", width=s(2.6))

    for px in (x0 + 44, x1 - 44):
        draw.line([s(px), s(y0 + 17), s(px - 10), s(y1 - 4)], fill="#9D174D", width=s(2.6))
        draw.line([s(px), s(y0 + 17), s(px + 10), s(y1 - 4)], fill="#9D174D", width=s(2.6))
        draw.line([s(px - 14), s(y0 + 27), s(px + 14), s(y0 + 27)], fill="#9D174D", width=s(2.6))
    draw.arc([s(x0 + 44), s(y0 + 13), s(x1 - 44), s(y0 + 45)], start=0, end=180, fill="#F59E0B", width=s(2.8))


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
    # Soft hairline editorial card outline
    rounded_rect(draw, rect, radius=8, fill=CARD_BG, outline=HAIRLINE, width=1.0)

    strip_h = 26.0
    top_rounded_strip(draw, x0 + 1, y0 + 1, x1 - 1, y0 + strip_h, radius=7, fill=color)
    tag_font = load_font(SANS_BLACK, 15.0)
    draw_left_text(draw, x0 + 10, y0 + strip_h / 2, tag, tag_font, "#FFFFFF")

    art_box = (x0 + 2, y0 + strip_h, x1 - 2, y0 + strip_h + 77)
    art_fn(draw, art_box)
    draw.line([s(x0 + 1), s(art_box[3]), s(x1 - 1), s(art_box[3])], fill="#E8E1D1", width=s(1.0))

    # Giant 21px Lato-Black sans-serif headline (zero thin serif hairlines at 300px!)
    hl_font = load_font(SANS_BLACK, 21.0)
    mid_y = (art_box[3] + y1) / 2
    ys = [mid_y - 13.0, mid_y + 13.0] if len(headline_lines) == 2 else [mid_y]
    for line, ly in zip(headline_lines, ys):
        b = draw_centered_text(draw, (x0 + x1) / 2, ly, line, hl_font, INK)
        audit_boxes.append((f"card_hl:{line}", b))
        assert b[0] >= x0 + 5 and b[2] <= x1 - 5, f"Card headline clipped: '{line}' ({b[0]:.1f}..{b[2]:.1f} vs {x0+5}..{x1-5})"


def draw_wire_footer(
    draw: ImageDraw.ImageDraw,
    rect: tuple[float, float, float, float],
    audit_boxes: list[tuple[str, tuple[float, float, float, float]]],
) -> None:
    x0, y0, x1, y1 = rect
    rounded_rect(draw, rect, radius=8, fill=NAVY_DARK)
    top_rounded_strip(draw, x0, y0, x1, y0 + 4, radius=7, fill=GOLD)

    items = [
        ("GULF · OIL", "#EA580C", "Saudi & Japan add 16M bbl oil storage"),
        ("EU · CIVIC", "#2563EB", "Cost-of-living protests hit Europe"),
        ("SPORT · NZ", "#D97706", "NZ holds India to Wellington draw"),
        ("SCIENCE", "#0D9488", "Study: Ruler Verica likely female"),
    ]

    badge_font = load_font(SANS_BLACK, 15.0)
    text_font = load_font(SANS_BOLD, 17.5)

    col_w = (x1 - x0 - 24) / 2
    row_ys = [y0 + 26, y0 + 64]

    mid_x = (x0 + x1) / 2
    draw.line([s(mid_x), s(y0 + 12), s(mid_x), s(y1 - 10)], fill="#243B53", width=s(1.0))
    draw.line([s(x0 + 12), s(y0 + 45), s(x1 - 12), s(y0 + 45)], fill="#1E3349", width=s(1.0))

    for idx, (badge, bcol, headline) in enumerate(items):
        col = idx % 2
        row = idx // 2
        cx0 = x0 + 12 + col * (col_w + 10)
        cy = row_ys[row]
        bw = 114.0
        bh = 25.0
        brect = (cx0, cy - bh / 2, cx0 + bw, cy + bh / 2)
        rounded_rect(draw, brect, radius=5, fill=bcol)
        draw_centered_text(draw, cx0 + bw / 2, cy, badge, badge_font, "#FFFFFF")

        tb = draw_left_text(draw, cx0 + bw + 10, cy, headline, text_font, "#F8FAFC")
        audit_boxes.append((f"wire:{headline}", tb))
        col_limit = (mid_x - 8) if col == 0 else (x1 - 10)
        assert tb[2] <= col_limit, f"Wire text clipped: '{headline}' right={tb[2]:.1f} > {col_limit:.1f}"


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
    """Write a compact lossless adaptive-filtered 8-bit RGB PNG (colorType=2)."""
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

    # 1. TOP MASTHEAD (0..84px)
    draw.rectangle([0, 0, CW, s(26)], fill=NAVY_DARK)
    ribbon_font = load_font(SANS_BLACK, 15.0)
    draw_centered_text(draw, WIDTH / 2, 13, "WORLD NEWS ATLAS   ·   7 REGIONS   ·   15 STORIES", ribbon_font, GOLD_LIGHT)

    date_font = load_font(SERIF_BOLD, 48.0)
    date_box = draw_centered_text(draw, WIDTH / 2, 54, "Monday 23 November 2026", date_font, INK)
    audit_boxes.append(("masthead:date", date_box))

    # Crisp double archival rule
    draw.rectangle([s(12), s(80), s(WIDTH - 12), s(82)], fill=NAVY_DARK)
    draw.rectangle([s(12), s(83), s(WIDTH - 12), s(84.5)], fill=GOLD)

    # 2. UPPER VISUAL HERO (90..394px)
    draw_world_map(draw, (12, 90, 600, 394), audit_boxes)

    draw_lead_card(
        draw,
        (610, 90, 1012, 238),
        "LEAD 1  ·  GLOBAL · MARKETS",
        REGION_COLORS["GLOBAL"],
        ["AI Tech Rout Hits;", "Asia Launches Rescue"],
        ["China 16-mo low · Taiwan curbs", "Korea readies $8B support fund"],
        draw_lead1_art,
        audit_boxes,
    )
    draw_lead_card(
        draw,
        (610, 246, 1012, 394),
        "LEAD 2  ·  MIDDLE EAST · OIL",
        REGION_COLORS["MIDDLE_EAST"],
        ["Iran Vows Response", "to U.S. Oil Blockade"],
        ["Tehran vows all tools; U.S.", "warns blockade runners"],
        draw_lead2_art,
        audit_boxes,
    )

    # 3. MIDDLE VISUAL GALLERY: 3x3 HUGE PANORAMIC CARDS (402..922px)
    cards = [
        ("EUROPE · ENERGY", REGION_COLORS["EUROPE"], art_eu_gas, ["Europe Gas Jumps 6%", "to €93 on Cold Snap"]),
        ("AFRICA · OIL", REGION_COLORS["AFRICA"], art_libya_oil, ["Libya Valve Closure", "Cuts 350k bpd Oil"]),
        ("AMERICAS · ECONOMY", REGION_COLORS["AMERICAS"], art_us_fed, ["Bessent Warns Fed", "on Hawkish Rate Risk"]),
        ("ASIA · FINANCE", REGION_COLORS["ASIA"], art_sg_china_rmb, ["Singapore & China", "Expand RMB Liquidity"]),
        ("S. AMERICA · SPACE", REGION_COLORS["S_AMERICA"], art_ariane6, ["Ariane 6 Launch", "Halted at Kourou"]),
        ("OCEANIA · ECONOMY", REGION_COLORS["OCEANIA"], art_australia_econ, ["Australia Sees Slow", "Growth, No Recession"]),
        ("AFRICA · HEALTH", REGION_COLORS["AFRICA"], art_africa_health, ["Africa Public Health", "Summit Opens in Addis"]),
        ("EUROPE · MEDIA", REGION_COLORS["EUROPE"], art_bbc_media, ["Report Warns BBC", "Fee Faces Decline"]),
        ("S. ASIA · DIPLOMACY", REGION_COLORS["ASIA"], art_india_nepal, ["India & Nepal Sign", "Hydropower Pacts"]),
    ]

    col_xs = [(12, 337), (349, 675), (687, 1012)]
    row_ys = [(402, 568), (578, 744), (754, 920)]
    for idx, (tag, color, art_fn, lines) in enumerate(cards):
        r = idx // 3
        c = idx % 3
        cx0, cx1 = col_xs[c]
        ry0, ry1 = row_ys[r]
        draw_gallery_card(draw, (cx0, ry0, cx1, ry1), tag, color, art_fn, lines, audit_boxes)

    # 4. BOTTOM DARK-NAVY WIRE STRIP (930..1016px)
    draw_wire_footer(draw, (12, 930, 1012, 1016), audit_boxes)

    # Programmatic layout & overlap check
    issues = audit_overlaps(audit_boxes)
    if issues:
        raise RuntimeError("Layout audit failed:\n" + "\n".join(issues))

    # Exact 2x2 area average downsample (silky AA with zero Lanczos ringing)
    final = img.resize((WIDTH, HEIGHT), Image.Resampling.BOX).convert("RGB")
    size_bytes = save_compact_rgb_png(final, OUT_PNG)

    preview = final.resize((300, 300), Image.Resampling.LANCZOS)
    preview.save("/tmp/news23_v1_300px.png", format="PNG", optimize=True)

    print(
        f"Rendered {OUT_PNG} ({WIDTH}x{HEIGHT} 8-bit RGB, {size_bytes:,} bytes), "
        f"MIN_FONT_PX={MIN_FONT_PX}, layout audit: 0 issues ({len(audit_boxes)} boxes checked)."
    )


if __name__ == "__main__":
    render()
