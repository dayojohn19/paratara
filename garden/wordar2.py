import argparse
import math
import textwrap

import svgwrite
import cairosvg


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def path_cmd(commands):
    return " ".join(commands)


def add_path(
    dwg,
    group,
    d,
    stroke="#ffffff",
    stroke_width=10,
    fill="none",
    opacity=1.0,
):
    group.add(
        dwg.path(
            d=d,
            fill=fill,
            stroke=stroke,
            stroke_width=stroke_width,
            stroke_linecap="round",
            stroke_linejoin="round",
            opacity=opacity,
        )
    )


def draw_heart(dwg, group, cx, cy, size=20, fill="#d94f4f"):
    s = size

    d = path_cmd([
        f"M {cx} {cy + s}",
        f"C {cx - 2*s} {cy - s/2}, {cx - s} {cy - 2*s}, {cx} {cy - s}",
        f"C {cx + s} {cy - 2*s}, {cx + 2*s} {cy - s/2}, {cx} {cy + s}",
        "Z",
    ])

    group.add(dwg.path(d=d, fill=fill))


def draw_berry_cluster(dwg, group, x, y, color="#d9a044"):
    berries = [
        (x, y, 17),
        (x + 45, y + 18, 14),
        (x + 85, y - 5, 12),
    ]

    for cx, cy, r in berries:
        group.add(dwg.circle(center=(cx, cy), r=r, fill=color))
        group.add(dwg.circle(center=(cx - r * 0.3, cy - r * 0.35), r=r * 0.25, fill="#ffffff", opacity=0.7))


def draw_leaf_sprig(
    dwg,
    group,
    x,
    y,
    scale=1.0,
    flip=False,
    stroke="#65dbc7",
    fill="#65dbc7",
):
    direction = -1 if flip else 1

    end_x = x + direction * 190 * scale
    end_y = y - 85 * scale

    stem = path_cmd([
        f"M {x} {y}",
        f"C {x + direction * 55 * scale} {y - 45 * scale}, "
        f"{x + direction * 125 * scale} {y - 60 * scale}, "
        f"{end_x} {end_y}",
    ])

    add_path(
        dwg,
        group,
        stem,
        stroke=stroke,
        stroke_width=4 * scale,
        fill="none",
    )

    for i in range(7):
        t = i / 6
        lx = x + (end_x - x) * t
        ly = y + (end_y - y) * t

        side = -1 if i % 2 == 0 else 1
        side *= direction

        leaf = path_cmd([
            f"M {lx} {ly}",
            f"C {lx + side * 25 * scale} {ly - 24 * scale}, "
            f"{lx + side * 55 * scale} {ly - 20 * scale}, "
            f"{lx + side * 65 * scale} {ly - 2 * scale}",
            f"C {lx + side * 42 * scale} {ly + 12 * scale}, "
            f"{lx + side * 17 * scale} {ly + 10 * scale}, "
            f"{lx} {ly}",
            "Z",
        ])

        group.add(dwg.path(d=leaf, fill=fill))


def draw_flower(dwg, group, cx, cy, scale=1.0, fill="#d94f4f", center="#ffffff"):
    petals = [
        (cx, cy - 42 * scale),
        (cx + 40 * scale, cy - 10 * scale),
        (cx + 25 * scale, cy + 38 * scale),
        (cx - 25 * scale, cy + 38 * scale),
        (cx - 40 * scale, cy - 10 * scale),
    ]

    for px, py in petals:
        d = path_cmd([
            f"M {cx} {cy}",
            f"C {px - 28 * scale} {py - 20 * scale}, "
            f"{px - 22 * scale} {py + 22 * scale}, "
            f"{px} {py}",
            f"C {px + 22 * scale} {py + 22 * scale}, "
            f"{px + 28 * scale} {py - 20 * scale}, "
            f"{cx} {cy}",
            "Z",
        ])
        group.add(dwg.path(d=d, fill=fill))

    for dx, dy in [
        (0, 0),
        (13, 0),
        (-13, 0),
        (7, 12),
        (-7, 12),
        (7, -12),
        (-7, -12),
    ]:
        group.add(
            dwg.circle(
                center=(cx + dx * scale, cy + dy * scale),
                r=5 * scale,
                fill=center,
            )
        )


def draw_star(dwg, group, cx, cy, size=35, fill="#d9a044"):
    points = []
    for i in range(10):
        radius = size if i % 2 == 0 else size * 0.42
        angle = -90 + i * 36
        x = cx + radius * math.cos(math.radians(angle))
        y = cy + radius * math.sin(math.radians(angle))
        points.append((x, y))
    group.add(dwg.polygon(points=points, fill=fill))


def draw_balloon(dwg, group, cx, cy, scale=1.0, fill="#d94f4f"):
    group.add(dwg.ellipse(center=(cx, cy), r=(42 * scale, 55 * scale), fill=fill))
    group.add(
        dwg.circle(
            center=(cx - 14 * scale, cy - 18 * scale),
            r=9 * scale,
            fill="#ffffff",
            opacity=0.55,
        )
    )
    group.add(dwg.polygon(
        points=[
            (cx - 7 * scale, cy + 51 * scale),
            (cx + 7 * scale, cy + 51 * scale),
            (cx, cy + 68 * scale),
        ],
        fill=fill,
    ))
    add_path(
        dwg,
        group,
        path_cmd([
            f"M {cx} {cy + 68 * scale}",
            f"C {cx - 30 * scale} {cy + 115 * scale}, "
            f"{cx + 32 * scale} {cy + 150 * scale}, "
            f"{cx - 4 * scale} {cy + 200 * scale}",
        ]),
        stroke="#f7f2ff",
        stroke_width=3 * scale,
        fill="none",
    )


def draw_gift(dwg, group, x, y, scale=1.0, fill="#65dbc7", ribbon="#d94f4f"):
    group.add(dwg.rect(insert=(x, y + 40 * scale), size=(130 * scale, 105 * scale), fill=fill, rx=8 * scale))
    group.add(dwg.rect(insert=(x - 10 * scale, y + 18 * scale), size=(150 * scale, 35 * scale), fill=fill, rx=7 * scale))
    group.add(dwg.rect(insert=(x + 55 * scale, y + 18 * scale), size=(20 * scale, 127 * scale), fill=ribbon))
    group.add(dwg.rect(insert=(x - 10 * scale, y + 32 * scale), size=(150 * scale, 15 * scale), fill=ribbon))
    add_path(
        dwg,
        group,
        path_cmd([
            f"M {x + 65 * scale} {y + 20 * scale}",
            f"C {x + 20 * scale} {y - 42 * scale}, "
            f"{x + 18 * scale} {y + 52 * scale}, "
            f"{x + 65 * scale} {y + 22 * scale}",
            f"C {x + 112 * scale} {y - 42 * scale}, "
            f"{x + 114 * scale} {y + 52 * scale}, "
            f"{x + 65 * scale} {y + 22 * scale}",
        ]),
        stroke=ribbon,
        stroke_width=9 * scale,
        fill="none",
    )


def draw_snowflake(dwg, group, cx, cy, size=42, stroke="#9fe8ef"):
    for angle in (0, 60, 120):
        line = dwg.line(
            start=(cx - size, cy),
            end=(cx + size, cy),
            stroke=stroke,
            stroke_width=5,
            stroke_linecap="round",
        )
        line.rotate(angle, center=(cx, cy))
        group.add(line)
    group.add(dwg.circle(center=(cx, cy), r=size * 0.13, fill=stroke))


def draw_wave(dwg, group, x, y, scale=1.0, stroke="#9fe8ef"):
    for offset in (0, 38, 76):
        add_path(
            dwg,
            group,
            path_cmd([
                f"M {x} {y + offset * scale}",
                f"C {x + 70 * scale} {y - 45 * scale + offset * scale}, "
                f"{x + 130 * scale} {y + 45 * scale + offset * scale}, "
                f"{x + 205 * scale} {y + offset * scale}",
                f"C {x + 275 * scale} {y - 45 * scale + offset * scale}, "
                f"{x + 335 * scale} {y + 45 * scale + offset * scale}, "
                f"{x + 410 * scale} {y + offset * scale}",
            ]),
            stroke=stroke,
            stroke_width=8 * scale,
            fill="none",
        )


def draw_swash_top(dwg, group, x, y, scale=1.0, stroke="#f7f2ff", width=6):
    d = path_cmd([
        f"M {x} {y}",
        f"C {x + 130 * scale} {y - 150 * scale}, "
        f"{x + 420 * scale} {y - 120 * scale}, "
        f"{x + 360 * scale} {y + 20 * scale}",
        f"C {x + 310 * scale} {y + 120 * scale}, "
        f"{x + 190 * scale} {y + 80 * scale}, "
        f"{x + 250 * scale} {y + 20 * scale}",
        f"C {x + 330 * scale} {y - 60 * scale}, "
        f"{x + 610 * scale} {y - 50 * scale}, "
        f"{x + 710 * scale} {y + 80 * scale}",
    ])

    add_path(dwg, group, d, stroke=stroke, stroke_width=width, fill="none")


def draw_swash_bottom(dwg, group, x, y, scale=1.0, stroke="#f7f2ff", width=7):
    d = path_cmd([
        f"M {x} {y}",
        f"C {x - 220 * scale} {y + 110 * scale}, "
        f"{x + 120 * scale} {y + 190 * scale}, "
        f"{x + 500 * scale} {y + 105 * scale}",
        f"C {x + 850 * scale} {y + 25 * scale}, "
        f"{x + 1050 * scale} {y + 95 * scale}, "
        f"{x + 1100 * scale} {y + 10 * scale}",
        f"C {x + 1160 * scale} {y - 95 * scale}, "
        f"{x + 930 * scale} {y - 100 * scale}, "
        f"{x + 965 * scale} {y + 10 * scale}",
    ])

    add_path(dwg, group, d, stroke=stroke, stroke_width=width, fill="none")


# ------------------------------------------------------------
# Custom script letters
# ------------------------------------------------------------

def draw_capital_m(dwg, group, x, y, scale=1.0, stroke="#f7f2ff", width=14):
    d = path_cmd([
        f"M {x} {y + 165 * scale}",
        f"C {x - 80 * scale} {y + 125 * scale}, "
        f"{x - 55 * scale} {y + 10 * scale}, "
        f"{x + 32 * scale} {y + 55 * scale}",

        f"C {x + 110 * scale} {y + 95 * scale}, "
        f"{x + 65 * scale} {y + 225 * scale}, "
        f"{x + 18 * scale} {y + 220 * scale}",

        f"C {x - 35 * scale} {y + 215 * scale}, "
        f"{x - 5 * scale} {y + 130 * scale}, "
        f"{x + 62 * scale} {y + 72 * scale}",

        f"C {x + 125 * scale} {y + 18 * scale}, "
        f"{x + 170 * scale} {y + 62 * scale}, "
        f"{x + 150 * scale} {y + 160 * scale}",

        f"C {x + 205 * scale} {y + 35 * scale}, "
        f"{x + 285 * scale} {y + 38 * scale}, "
        f"{x + 265 * scale} {y + 165 * scale}",

        f"C {x + 305 * scale} {y + 110 * scale}, "
        f"{x + 350 * scale} {y + 108 * scale}, "
        f"{x + 390 * scale} {y + 126 * scale}",
    ])

    add_path(dwg, group, d, stroke=stroke, stroke_width=width, fill="none")
    return x + 390 * scale


def draw_capital_c(dwg, group, x, y, scale=1.0, stroke="#f7f2ff", width=14):
    d = path_cmd([
        f"M {x + 280 * scale} {y + 75 * scale}",
        f"C {x + 210 * scale} {y - 15 * scale}, "
        f"{x + 40 * scale} {y + 10 * scale}, "
        f"{x - 10 * scale} {y + 150 * scale}",

        f"C {x - 70 * scale} {y + 320 * scale}, "
        f"{x + 105 * scale} {y + 390 * scale}, "
        f"{x + 265 * scale} {y + 280 * scale}",

        f"C {x + 340 * scale} {y + 225 * scale}, "
        f"{x + 330 * scale} {y + 160 * scale}, "
        f"{x + 260 * scale} {y + 180 * scale}",
    ])

    add_path(dwg, group, d, stroke=stroke, stroke_width=width, fill="none")
    return x + 320 * scale


def draw_e(dwg, group, x, y, scale=1.0, stroke="#f7f2ff", width=11):
    d = path_cmd([
        f"M {x} {y + 122 * scale}",
        f"C {x + 45 * scale} {y + 55 * scale}, "
        f"{x + 130 * scale} {y + 65 * scale}, "
        f"{x + 97 * scale} {y + 130 * scale}",

        f"C {x + 72 * scale} {y + 175 * scale}, "
        f"{x + 15 * scale} {y + 148 * scale}, "
        f"{x + 62 * scale} {y + 107 * scale}",

        f"C {x + 105 * scale} {y + 70 * scale}, "
        f"{x + 150 * scale} {y + 128 * scale}, "
        f"{x + 180 * scale} {y + 116 * scale}",
    ])

    add_path(dwg, group, d, stroke=stroke, stroke_width=width, fill="none")
    return x + 168 * scale


def draw_r(dwg, group, x, y, scale=1.0, stroke="#f7f2ff", width=11):
    d = path_cmd([
        f"M {x} {y + 150 * scale}",
        f"C {x + 25 * scale} {y + 92 * scale}, "
        f"{x + 50 * scale} {y + 68 * scale}, "
        f"{x + 77 * scale} {y + 86 * scale}",

        f"C {x + 110 * scale} {y + 108 * scale}, "
        f"{x + 82 * scale} {y + 145 * scale}, "
        f"{x + 48 * scale} {y + 127 * scale}",

        f"C {x + 97 * scale} {y + 86 * scale}, "
        f"{x + 137 * scale} {y + 103 * scale}, "
        f"{x + 168 * scale} {y + 116 * scale}",
    ])

    add_path(dwg, group, d, stroke=stroke, stroke_width=width, fill="none")
    return x + 145 * scale


def draw_y(dwg, group, x, y, scale=1.0, stroke="#f7f2ff", width=11):
    d = path_cmd([
        f"M {x} {y + 92 * scale}",
        f"C {x + 22 * scale} {y + 165 * scale}, "
        f"{x + 78 * scale} {y + 160 * scale}, "
        f"{x + 100 * scale} {y + 92 * scale}",

        f"C {x + 62 * scale} {y + 230 * scale}, "
        f"{x - 25 * scale} {y + 280 * scale}, "
        f"{x - 72 * scale} {y + 235 * scale}",

        f"C {x - 118 * scale} {y + 190 * scale}, "
        f"{x - 55 * scale} {y + 158 * scale}, "
        f"{x + 38 * scale} {y + 172 * scale}",

        f"C {x + 118 * scale} {y + 185 * scale}, "
        f"{x + 160 * scale} {y + 130 * scale}, "
        f"{x + 190 * scale} {y + 116 * scale}",
    ])

    add_path(dwg, group, d, stroke=stroke, stroke_width=width, fill="none")
    return x + 165 * scale


def draw_h(dwg, group, x, y, scale=1.0, stroke="#f7f2ff", width=11):
    d = path_cmd([
        f"M {x} {y + 210 * scale}",
        f"C {x + 45 * scale} {y + 75 * scale}, "
        f"{x + 60 * scale} {y - 10 * scale}, "
        f"{x + 18 * scale} {y + 30 * scale}",

        f"C {x - 35 * scale} {y + 85 * scale}, "
        f"{x - 18 * scale} {y + 180 * scale}, "
        f"{x + 50 * scale} {y + 135 * scale}",

        f"C {x + 110 * scale} {y + 95 * scale}, "
        f"{x + 120 * scale} {y + 145 * scale}, "
        f"{x + 98 * scale} {y + 210 * scale}",

        f"C {x + 135 * scale} {y + 140 * scale}, "
        f"{x + 175 * scale} {y + 115 * scale}, "
        f"{x + 220 * scale} {y + 120 * scale}",
    ])

    add_path(dwg, group, d, stroke=stroke, stroke_width=width, fill="none")
    return x + 200 * scale


def draw_i(dwg, group, x, y, scale=1.0, stroke="#f7f2ff", width=11):
    d = path_cmd([
        f"M {x} {y + 145 * scale}",
        f"C {x + 20 * scale} {y + 105 * scale}, "
        f"{x + 45 * scale} {y + 100 * scale}, "
        f"{x + 52 * scale} {y + 125 * scale}",

        f"C {x + 60 * scale} {y + 160 * scale}, "
        f"{x + 25 * scale} {y + 175 * scale}, "
        f"{x + 78 * scale} {y + 118 * scale}",
    ])

    add_path(dwg, group, d, stroke=stroke, stroke_width=width, fill="none")

    group.add(
        dwg.circle(
            center=(x + 50 * scale, y + 65 * scale),
            r=7 * scale,
            fill=stroke,
        )
    )

    return x + 80 * scale


def draw_s(dwg, group, x, y, scale=1.0, stroke="#f7f2ff", width=11):
    d = path_cmd([
        f"M {x + 115 * scale} {y + 92 * scale}",
        f"C {x + 55 * scale} {y + 45 * scale}, "
        f"{x - 15 * scale} {y + 82 * scale}, "
        f"{x + 22 * scale} {y + 132 * scale}",

        f"C {x + 58 * scale} {y + 178 * scale}, "
        f"{x + 120 * scale} {y + 132 * scale}, "
        f"{x + 92 * scale} {y + 102 * scale}",

        f"C {x + 58 * scale} {y + 65 * scale}, "
        f"{x + 20 * scale} {y + 160 * scale}, "
        f"{x + 125 * scale} {y + 120 * scale}",
    ])

    add_path(dwg, group, d, stroke=stroke, stroke_width=width, fill="none")
    return x + 120 * scale


def draw_t(dwg, group, x, y, scale=1.0, stroke="#f7f2ff", width=11):
    d1 = path_cmd([
        f"M {x + 65 * scale} {y + 25 * scale}",
        f"C {x + 20 * scale} {y + 115 * scale}, "
        f"{x + 20 * scale} {y + 205 * scale}, "
        f"{x + 85 * scale} {y + 155 * scale}",

        f"C {x + 115 * scale} {y + 132 * scale}, "
        f"{x + 130 * scale} {y + 120 * scale}, "
        f"{x + 160 * scale} {y + 118 * scale}",
    ])

    d2 = path_cmd([
        f"M {x + 20 * scale} {y + 85 * scale}",
        f"C {x + 72 * scale} {y + 65 * scale}, "
        f"{x + 120 * scale} {y + 65 * scale}, "
        f"{x + 170 * scale} {y + 82 * scale}",
    ])

    add_path(dwg, group, d1, stroke=stroke, stroke_width=width, fill="none")
    add_path(dwg, group, d2, stroke=stroke, stroke_width=width * 0.75, fill="none")

    return x + 150 * scale


def draw_a(dwg, group, x, y, scale=1.0, stroke="#f7f2ff", width=11):
    d = path_cmd([
        f"M {x + 95 * scale} {y + 92 * scale}",
        f"C {x + 30 * scale} {y + 70 * scale}, "
        f"{x - 5 * scale} {y + 165 * scale}, "
        f"{x + 58 * scale} {y + 160 * scale}",

        f"C {x + 110 * scale} {y + 155 * scale}, "
        f"{x + 125 * scale} {y + 72 * scale}, "
        f"{x + 98 * scale} {y + 92 * scale}",

        f"C {x + 85 * scale} {y + 135 * scale}, "
        f"{x + 112 * scale} {y + 165 * scale}, "
        f"{x + 170 * scale} {y + 118 * scale}",
    ])

    add_path(dwg, group, d, stroke=stroke, stroke_width=width, fill="none")
    return x + 150 * scale


# ------------------------------------------------------------
# Word drawers
# ------------------------------------------------------------

def draw_word_merry(dwg, group, x, y, scale=1.0, stroke="#f7f2ff"):
    x = draw_capital_m(dwg, group, x, y, scale, stroke, width=15 * scale)
    x = draw_e(dwg, group, x - 15 * scale, y + 35 * scale, scale, stroke, width=12 * scale)
    x = draw_r(dwg, group, x - 20 * scale, y + 35 * scale, scale, stroke, width=12 * scale)
    x = draw_r(dwg, group, x - 45 * scale, y + 35 * scale, scale, stroke, width=12 * scale)
    x = draw_y(dwg, group, x - 45 * scale, y + 35 * scale, scale, stroke, width=12 * scale)
    return x


def draw_word_christmas(dwg, group, x, y, scale=1.0, stroke="#f7f2ff"):
    x = draw_capital_c(dwg, group, x, y, scale, stroke, width=15 * scale)
    x = draw_h(dwg, group, x - 40 * scale, y + 65 * scale, scale, stroke, width=12 * scale)
    x = draw_r(dwg, group, x - 25 * scale, y + 95 * scale, scale, stroke, width=12 * scale)
    x = draw_i(dwg, group, x - 35 * scale, y + 95 * scale, scale, stroke, width=12 * scale)
    x = draw_s(dwg, group, x - 10 * scale, y + 95 * scale, scale, stroke, width=12 * scale)
    x = draw_t(dwg, group, x - 20 * scale, y + 75 * scale, scale, stroke, width=12 * scale)
    x = draw_m_lower(dwg, group, x - 25 * scale, y + 95 * scale, scale, stroke, width=12 * scale)
    x = draw_a(dwg, group, x - 20 * scale, y + 95 * scale, scale, stroke, width=12 * scale)
    x = draw_s(dwg, group, x - 25 * scale, y + 95 * scale, scale, stroke, width=12 * scale)
    return x


def draw_m_lower(dwg, group, x, y, scale=1.0, stroke="#f7f2ff", width=11):
    d = path_cmd([
        f"M {x} {y + 155 * scale}",
        f"C {x + 25 * scale} {y + 90 * scale}, "
        f"{x + 65 * scale} {y + 70 * scale}, "
        f"{x + 82 * scale} {y + 155 * scale}",

        f"C {x + 105 * scale} {y + 90 * scale}, "
        f"{x + 145 * scale} {y + 70 * scale}, "
        f"{x + 162 * scale} {y + 155 * scale}",

        f"C {x + 185 * scale} {y + 105 * scale}, "
        f"{x + 225 * scale} {y + 105 * scale}, "
        f"{x + 250 * scale} {y + 120 * scale}",
    ])

    add_path(dwg, group, d, stroke=stroke, stroke_width=width, fill="none")
    return x + 235 * scale


# ------------------------------------------------------------
# Main generator
# ------------------------------------------------------------

THEME_KEYWORDS = {
    "christmas": ("christmas", "xmas", "santa", "holiday", "merry", "snow", "winter"),
    "birthday": ("birthday", "bday", "born", "party", "cake", "celebrate"),
    "love": ("love", "valentine", "anniversary", "heart", "wedding"),
    "beach": ("beach", "summer", "ocean", "sea", "surf", "pool", "resort"),
}


def infer_theme(text):
    normalized = (text or "").lower()
    for theme, keywords in THEME_KEYWORDS.items():
        if any(keyword in normalized for keyword in keywords):
            return theme
    return "floral"


def split_text_lines(text, max_chars=16):
    cleaned = " ".join((text or "").split())
    if not cleaned:
        return ["Merry", "Christmas"]
    lines = textwrap.wrap(cleaned, width=max_chars, break_long_words=False)
    if not lines:
        return [cleaned]
    return lines[:3]


def text_style_for_lines(lines):
    longest = max(len(line) for line in lines)
    if len(lines) == 1:
        font_size = 250 if longest <= 10 else 210 if longest <= 16 else 165
    elif len(lines) == 2:
        font_size = 205 if longest <= 12 else 170 if longest <= 18 else 140
    else:
        font_size = 150 if longest <= 14 else 125
    return font_size


def draw_generic_wordart_text(dwg, root, text, main_color="#f7f2ff", highlight_color="#ffffff"):
    lines = split_text_lines(text)
    font_size = text_style_for_lines(lines)
    line_height = font_size * 1.05
    start_y = 420 - ((len(lines) - 1) * line_height / 2)
    font_family = "Brush Script MT, Snell Roundhand, Apple Chancery, Pacifico, cursive"

    shadow = dwg.g(id="soft_shadow", transform="translate(10, 14)", opacity=0.32)
    lettering = dwg.g(id="main_lettering")
    highlight = dwg.g(id="text_highlight", transform="translate(-4, -6)", opacity=0.30)

    draw_swash_top(dwg, shadow, 500, 130, 1.0, stroke="#000000", width=7)
    draw_swash_bottom(dwg, shadow, 185, 820, 1.0, stroke="#000000", width=8)
    draw_swash_top(dwg, lettering, 500, 130, 1.0, stroke=main_color, width=7)
    draw_swash_bottom(dwg, lettering, 185, 820, 1.0, stroke=main_color, width=8)

    for index, line in enumerate(lines):
        y = start_y + index * line_height
        attrs = {
            "insert": (800, y),
            "text_anchor": "middle",
            "dominant_baseline": "middle",
            "font_size": font_size,
            "font_family": font_family,
            "font_weight": "600",
        }
        shadow.add(dwg.text(line, fill="#000000", **attrs))
        lettering.add(dwg.text(line, fill=main_color, **attrs))
        highlight.add(dwg.text(line, fill=highlight_color, **attrs))

    root.add(shadow)
    root.add(lettering)
    root.add(highlight)


def draw_original_merry_christmas_text(dwg, root, main_color="#f7f2ff", highlight_color="#ffffff"):
    shadow = dwg.g(id="soft_shadow", transform="translate(10, 14)", opacity=0.30)

    draw_swash_top(dwg, shadow, 500, 130, 1.0, stroke="#000000", width=7)
    draw_word_merry(dwg, shadow, 290, 210, 1.25, stroke="#000000")
    draw_word_christmas(dwg, shadow, 130, 480, 1.08, stroke="#000000")
    draw_swash_bottom(dwg, shadow, 185, 820, 1.0, stroke="#000000", width=8)

    root.add(shadow)

    lettering = dwg.g(id="main_lettering")

    draw_swash_top(dwg, lettering, 500, 130, 1.0, stroke=main_color, width=7)
    draw_word_merry(dwg, lettering, 290, 210, 1.25, stroke=main_color)
    draw_word_christmas(dwg, lettering, 130, 480, 1.08, stroke=main_color)
    draw_swash_bottom(dwg, lettering, 185, 820, 1.0, stroke=main_color, width=8)

    root.add(lettering)

    highlight = dwg.g(id="text_highlight", transform="translate(-4, -6)", opacity=0.32)

    draw_word_merry(dwg, highlight, 290, 210, 1.25, stroke=highlight_color)
    draw_word_christmas(dwg, highlight, 130, 480, 1.08, stroke=highlight_color)

    root.add(highlight)


def draw_decorations(dwg, root, theme):
    decor = dwg.g(id=f"{theme}_decorations")

    red = "#d94f4f"
    teal = "#65dbc7"
    blue = "#9fe8ef"
    gold = "#d9a044"
    white = "#ffffff"
    pink = "#f28ab2"
    orange = "#f4a340"

    if theme == "birthday":
        draw_balloon(dwg, decor, 210, 230, scale=1.05, fill=red)
        draw_balloon(dwg, decor, 1330, 240, scale=0.95, fill=teal)
        draw_balloon(dwg, decor, 1440, 500, scale=0.75, fill=gold)
        draw_gift(dwg, decor, 180, 785, scale=1.0, fill=teal, ribbon=red)
        draw_gift(dwg, decor, 1230, 760, scale=0.85, fill=gold, ribbon=pink)
        for point in ((430, 160), (1090, 145), (520, 875), (980, 850)):
            draw_star(dwg, decor, *point, size=32, fill=gold)
        draw_berry_cluster(dwg, decor, 710, 820, color=pink)
    elif theme == "love":
        for cx, cy, size, fill in (
            (240, 250, 38, red),
            (1370, 250, 34, pink),
            (1260, 670, 30, red),
            (360, 770, 28, pink),
            (760, 165, 22, white),
        ):
            draw_heart(dwg, decor, cx, cy, size=size, fill=fill)
        draw_flower(dwg, decor, 455, 875, scale=1.15, fill=pink)
        draw_flower(dwg, decor, 1140, 125, scale=0.92, fill=red)
        draw_leaf_sprig(dwg, decor, 95, 340, scale=1.15, flip=False, stroke=teal, fill=teal)
        draw_leaf_sprig(dwg, decor, 1430, 845, scale=1.15, flip=True, stroke=teal, fill=teal)
    elif theme == "beach":
        draw_wave(dwg, decor, 95, 805, scale=1.05, stroke=blue)
        draw_wave(dwg, decor, 1010, 165, scale=0.85, stroke=teal)
        draw_star(dwg, decor, 240, 240, size=58, fill=gold)
        draw_star(dwg, decor, 1340, 700, size=45, fill=orange)
        draw_berry_cluster(dwg, decor, 470, 850, color=orange)
        draw_leaf_sprig(dwg, decor, 80, 370, scale=1.0, flip=False, stroke=teal, fill=teal)
        draw_leaf_sprig(dwg, decor, 1450, 440, scale=0.95, flip=True, stroke=teal, fill=teal)
    elif theme == "christmas":
        draw_flower(dwg, decor, 440, 880, scale=1.15, fill=red)
        draw_flower(dwg, decor, 1150, 120, scale=0.9, fill=red)
        draw_heart(dwg, decor, 405, 215, size=20, fill=white)
        draw_heart(dwg, decor, 760, 195, size=18, fill=red)
        draw_heart(dwg, decor, 1190, 460, size=18, fill=white)
        draw_heart(dwg, decor, 1240, 640, size=20, fill=red)
        draw_heart(dwg, decor, 170, 880, size=16, fill=red)
        draw_berry_cluster(dwg, decor, 590, 820, color=gold)
        draw_berry_cluster(dwg, decor, 1280, 630, color=red)
        draw_berry_cluster(dwg, decor, 260, 150, color=gold)
        draw_snowflake(dwg, decor, 1335, 195, size=40, stroke=blue)
        draw_snowflake(dwg, decor, 215, 690, size=34, stroke=white)
        draw_leaf_sprig(dwg, decor, 80, 310, scale=1.2, flip=False, stroke=teal, fill=teal)
        draw_leaf_sprig(dwg, decor, 1450, 360, scale=1.0, flip=True, stroke=teal, fill=teal)
        draw_leaf_sprig(dwg, decor, 850, 850, scale=1.05, flip=False, stroke=blue, fill=blue)
        draw_leaf_sprig(dwg, decor, 1380, 870, scale=1.25, flip=True, stroke=teal, fill=teal)
        draw_leaf_sprig(dwg, decor, 1080, 310, scale=0.8, flip=False, stroke=teal, fill=teal)
    else:
        draw_flower(dwg, decor, 350, 825, scale=1.2, fill=red)
        draw_flower(dwg, decor, 1180, 170, scale=1.0, fill=pink)
        draw_flower(dwg, decor, 1280, 775, scale=0.85, fill=gold)
        draw_heart(dwg, decor, 260, 210, size=18, fill=white)
        draw_heart(dwg, decor, 1320, 535, size=20, fill=red)
        draw_berry_cluster(dwg, decor, 590, 820, color=gold)
        draw_berry_cluster(dwg, decor, 260, 150, color=pink)
        draw_leaf_sprig(dwg, decor, 80, 310, scale=1.2, flip=False, stroke=teal, fill=teal)
        draw_leaf_sprig(dwg, decor, 1450, 360, scale=1.0, flip=True, stroke=teal, fill=teal)
        draw_leaf_sprig(dwg, decor, 850, 850, scale=1.05, flip=False, stroke=blue, fill=blue)

    root.add(decor)


def generate_christmas_wordart_svg(
    svg_path="christmas_wordart.svg",
    png_path="christmas_wordart.png",
    export_png=True,
    text="Merry Christmas",
    theme=None,
):
    width = 1600
    height = 1050

    dwg = svgwrite.Drawing(
        svg_path,
        size=(width, height),
        viewBox=f"0 0 {width} {height}",
    )

    root = dwg.g(id="transparent_wordart")

    main_color = "#f7f2ff"
    highlight_color = "#ffffff"
    selected_theme = theme or infer_theme(text)

    if " ".join(text.lower().split()) == "merry christmas":
        draw_original_merry_christmas_text(dwg, root, main_color, highlight_color)
    else:
        draw_generic_wordart_text(dwg, root, text, main_color, highlight_color)

    draw_decorations(dwg, root, selected_theme)

    dwg.add(root)
    dwg.save()

    if export_png:
        cairosvg.svg2png(
            url=svg_path,
            write_to=png_path,
            output_width=2400,
            output_height=1575,
        )

    return svg_path, png_path if export_png else None


def generate_wordart_svg(
    text="Merry Christmas",
    svg_path="garden/wordart_custom.svg",
    png_path="garden/wordart_custom.png",
    export_png=True,
    theme=None,
):
    return generate_christmas_wordart_svg(
        svg_path=svg_path,
        png_path=png_path,
        export_png=export_png,
        text=text,
        theme=theme,
    )


# ------------------------------------------------------------
# Run
# ------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate transparent word art SVG/PNG.")
    parser.add_argument("text", nargs="?", default="Merry Christmas")
    parser.add_argument("--theme", choices=["christmas", "birthday", "love", "beach", "floral"])
    parser.add_argument("--svg", default="garden/christmas_wordart.svg")
    parser.add_argument("--png", default="garden/christmas_wordart.png")
    parser.add_argument("--svg-only", action="store_true")
    args = parser.parse_args()

    svg_file, png_file = generate_christmas_wordart_svg(
        svg_path=args.svg,
        png_path=args.png,
        export_png=not args.svg_only,
        text=args.text,
        theme=args.theme,
    )

    print("Created:", svg_file)
    if png_file:
        print("Created:", png_file)
