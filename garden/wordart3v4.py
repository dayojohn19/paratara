from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageStat
import os, math, random


# =============================================================
#  FONTS
# =============================================================
_G = "garden/assets/fonts"

_FALLBACK = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "C:/Windows/Fonts/arialbd.ttf",
    "DejaVuSans-Bold.ttf",
]

_CJK_FALLBACK = [
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansJP-Regular.otf",
    "/usr/share/fonts/truetype/noto/NotoSansKR-Regular.otf",
    "/usr/share/fonts/truetype/noto/NotoSansSC-Regular.otf",
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/YuGothR.ttc",
]

def _can_load(path):
    """Return True if PIL can actually open this font file."""
    if not path or not os.path.exists(path):
        return False
    try:
        ImageFont.truetype(path, 20)
        return True
    except Exception:
        return False


def _pick(paths, randomize=False):
    """Return the first path that PIL can actually load."""
    ok = [p for p in paths if _can_load(p)]
    if not ok:
        return None
    return random.choice(ok) if randomize else ok[0]


_SYS_FALLBACK_CACHE = None

def _sys_fallback():
    """Return a system font that PIL can actually load. Cached."""
    global _SYS_FALLBACK_CACHE
    if _SYS_FALLBACK_CACHE:
        return _SYS_FALLBACK_CACHE
    for p in _FALLBACK:
        if _can_load(p):
            _SYS_FALLBACK_CACHE = p
            return p
    # Last resort: enumerate whatever PIL can find
    for p in find_font_paths() if "find_font_paths" in globals() else []:
        if _can_load(p):
            _SYS_FALLBACK_CACHE = p
            return p
    raise RuntimeError(
        "No usable font found. Install DejaVu Sans or Arial, or run "
        "download_fonts.py to fetch the bundled fonts."
    )
def load_fonts():
    fonts = {
        "display": _pick([
            f"{_G}/Anton/Anton-Regular.ttf",
            f"{_G}/ArchivoBlack/ArchivoBlack-Regular.ttf",
            f"{_G}/AbrilFatface/AbrilFatface-Regular.ttf",
        ]),
        "condensed": _pick([
            f"{_G}/BebasNeue/BebasNeue-Regular.ttf",
            f"{_G}/Oswald/Oswald-Bold.ttf",
            f"{_G}/Staatliches/Staatliches-Regular.ttf",
        ]),
        "serif": _pick([
            f"{_G}/PlayfairDisplay/PlayfairDisplay-Bold.ttf",
            f"{_G}/Cinzel/Cinzel-Bold.ttf",
        ]),
        "serif_reg": _pick([
            f"{_G}/PlayfairDisplay/PlayfairDisplay-Regular.ttf",
            f"{_G}/Cinzel/Cinzel-Regular.ttf",
        ]),
        "script": _pick([
            f"{_G}/GreatVibes/GreatVibes-Regular.ttf",
            f"{_G}/Pacifico/Pacifico-Regular.ttf",
            f"{_G}/DancingScript/DancingScript-Bold.ttf",
        ]),
        "marker": _pick([
            f"{_G}/PermanentMarker/PermanentMarker-Regular.ttf",
            f"{_G}/Caveat/Caveat-Bold.ttf",
        ]),
        "sans": _pick([
            f"{_G}/helvetica-255/Helvetica-Bold.ttf",
            f"{_G}/helvetica-255/helvetica-rounded-bold-5871d05ead8de.otf",
            f"{_G}/PlayfairDisplay/PlayfairDisplay-Bold.ttf",
            f"{_G}/Oswald/Oswald-Bold.ttf",
        ]),
    }
    fb = _sys_fallback()
    for k in fonts:
        if not fonts[k]:
            fonts[k] = fb
    return fonts
def _cjk_font(explicit=None):
    if explicit and _can_load(explicit):
        return explicit
    return _pick(_CJK_FALLBACK) or _sys_fallback()

def _is_ascii(s):
    return all(ord(c) < 128 for c in s)


# =============================================================
#  PALETTES  —  hand-tuned, art-directed
# =============================================================
# Each palette is designed to work on ANY photo:
#   text    = light, for main text
#   outline = dark, 1-2px stroke so light text pops on light bgs
#   accent  = rules, ornaments, thin lines
#   band    = dark color for solid bands / badges / stamps
PALETTES = {
    "ivory_navy": {
        "text":    (250, 245, 232),
        "outline": (14, 24, 46),
        "accent":  (216, 174, 92),
        "band":    (14, 24, 46),
    },
    "cream_burgundy": {
        "text":    (250, 244, 226),
        "outline": (72, 22, 32),
        "accent":  (206, 154, 86),
        "band":    (72, 22, 32),
    },
    "white_forest": {
        "text":    (248, 248, 244),
        "outline": (26, 58, 42),
        "accent":  (176, 198, 118),
        "band":    (26, 58, 42),
    },
    "sand_teal": {
        "text":    (252, 246, 232),
        "outline": (16, 58, 68),
        "accent":  (232, 138, 92),
        "band":    (16, 58, 68),
    },
    "ink_white": {
        "text":    (248, 248, 248),
        "outline": (18, 18, 20),
        "accent":  (188, 188, 192),
        "band":    (18, 18, 20),
    },
    "blush_plum": {
        "text":    (250, 240, 240),
        "outline": (66, 28, 56),
        "accent":  (226, 158, 166),
        "band":    (66, 28, 56),
    },
    "sunset_ember": {
        "text":    (254, 248, 234),
        "outline": (54, 22, 12),
        "accent":  (236, 138, 60),
        "band":    (54, 22, 12),
    },
    "slate_copper": {
        "text":    (246, 246, 240),
        "outline": (38, 44, 54),
        "accent":  (200, 118, 68),
        "band":    (38, 44, 54),
    },
    "warm_charcoal": {
        "text":    (245, 240, 232),
        "outline": (28, 26, 24),
        "accent":  (200, 160, 100),
        "band":    (28, 26, 24),
    },
}


def _lum(rgb):
    return (0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]) / 255.0


def pick_palette(mode="auto", bg_lum=None):
    if mode in PALETTES:
        return dict(PALETTES[mode])
    keys = list(PALETTES.keys())
    if bg_lum is None:
        return dict(PALETTES[random.choice(keys)])
    # Auto: pick the palette whose BAND contrasts most with the bg.
    # (Dark band on bright bg, dark band on dark bg → still works because
    # the band has its own solid fill; but for max contrast we prefer
    # palettes that differ most from the bg luminance.)
    target = 0.5  # we want the band to sit far from bg_lum
    return dict(max(keys, key=lambda k: abs(_lum(PALETTES[k]["band"]) - bg_lum)))


# =============================================================
#  BACKGROUND ANALYSIS
# =============================================================
def _region_stats(gray, box):
    region = gray.crop(box)
    edges = region.filter(ImageFilter.FIND_EDGES)
    busy = ImageStat.Stat(edges).mean[0] / 255.0
    lum = ImageStat.Stat(region).mean[0] / 255.0
    return busy, lum


def analyze_background(bg_img, canvas_size):
    W, H = canvas_size
    gray = bg_img.resize(canvas_size, Image.Resampling.LANCZOS).convert("L")

    bands = {
        "top":    (0, 0, W, int(H * 0.35)),
        "center": (0, int(H * 0.35), W, int(H * 0.65)),
        "bottom": (0, int(H * 0.65), W, H),
    }
    band_scores = {k: _region_stats(gray, v)[0] for k, v in bands.items()}
    band_scores["bottom"] -= 0.03   # bias: postcards usually bottom-caption
    position = min(band_scores, key=band_scores.get)

    quads = {
        "tl": (0, 0, W // 2, H // 2),
        "tr": (W // 2, 0, W, H // 2),
        "bl": (0, H // 2, W // 2, H),
        "br": (W // 2, H // 2, W, H),
    }
    q_scores = {k: _region_stats(gray, v)[0] for k, v in quads.items()}
    q_scores["br"] -= 0.02
    q_scores["bl"] -= 0.02
    corner = min(q_scores, key=q_scores.get)

    return {
        "position": position,
        "corner":   corner,
        "luminance": _region_stats(gray, bands[position])[1],
        "corner_luminance": _region_stats(gray, quads[corner])[1],
    }


# =============================================================
#  TEXT UTILITIES
# =============================================================
def _tracked_width(draw, text, font, tracking):
    if not text:
        return 0
    w = sum(draw.textlength(c, font=font) for c in text)
    return w + tracking * (len(text) - 1)


def _text_height(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[3] - bbox[1]


def _fit(draw, text, font_path, max_w, max_h,
         tracking_em=0.0, start=300, min_size=10):
    """Find the largest size where text fits. Falls back through system fonts."""
    # Validate once up front
    if not _can_load(font_path):
        font_path = _sys_fallback()

    size = start
    last_ok = None
    while size >= min_size:
        try:
            font = ImageFont.truetype(font_path, size)
        except Exception:
            size -= 2
            continue
        tracking = size * tracking_em
        w = _tracked_width(draw, text, font, tracking)
        h = _text_height(draw, text, font)
        last_ok = (font, tracking)
        if w <= max_w and h <= max_h:
            return font, tracking
        size -= 2

    # If we exhausted sizes and the font still loads, return the smallest
    try:
        font = ImageFont.truetype(font_path, min_size)
    except Exception:
        font = ImageFont.truetype(_sys_fallback(), min_size)
    return font, min_size * tracking_em

def _draw_tracked(draw, x, y, text, font, tracking, fill,
                  stroke_width=0, stroke_fill=None):
    """Draw text with per-character tracking. (x, y) is em-box top-left."""
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill,
                  stroke_width=stroke_width, stroke_fill=stroke_fill)
        x += draw.textlength(ch, font=font) + tracking


def _draw_centered(draw, cx, cy, text, font, tracking, fill,
                   stroke_width=0, stroke_fill=None):
    """Draw text horizontally centered at cx, vertically centered at cy."""
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    tw = _tracked_width(draw, text, font, tracking)
    th = bbox[3] - bbox[1]
    x = cx - tw / 2
    y = cy - th / 2 - bbox[1]
    _draw_tracked(draw, x, y, text, font, tracking, fill,
                  stroke_width, stroke_fill)


def _draw_centered_shadow(draw, cx, cy, text, font, tracking, palette,
                          shadow=3, stroke_width=1):
    """Centered text with a soft offset shadow and outline."""
    _draw_centered(draw, cx + shadow, cy + shadow, text, font, tracking,
                   palette["outline"], 0, None)
    _draw_centered(draw, cx, cy, text, font, tracking, palette["text"],
                   stroke_width, palette["outline"])


# =============================================================
#  PRESETS
#  Each preset returns a full-canvas RGBA overlay.
# =============================================================
TEXT_PRESETS  = {"editorial", "poster", "vintage", "minimal", "layered"}
BADGE_PRESETS = {"stamp", "band", "polaroid"}

ALL_PRESETS = TEXT_PRESETS | BADGE_PRESETS


# ---------- 1. EDITORIAL ----------
def _p_editorial(W, H, title, subtitle, prefix, palette, fonts, placement):
    """Small-caps sans + thin rules. The most versatile premium look."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # --- Fit sizes ---
    main_size_box = (W * 0.66, H * 0.14)
    main_font, main_tr = _fit(d, title.upper(), fonts["sans"],
                              *main_size_box, tracking_em=0.24, start=240, min_size=16)
    main_w = _tracked_width(d, title.upper(), main_font, main_tr)
    main_h = _text_height(d, title.upper(), main_font)

    sub_font = sub_tr = None
    sub_w = sub_h = 0
    if subtitle:
        sub_is_ascii = _is_ascii(subtitle)
        sub_path = fonts["sans"] if sub_is_ascii else _cjk_font()
        sub_track_em = 0.55 if sub_is_ascii else 0.12
        sub_font, sub_tr = _fit(d, subtitle.upper(), sub_path,
                                W * 0.62, H * 0.075,
                                tracking_em=sub_track_em, start=120, min_size=11)
        sub_w = _tracked_width(d, subtitle.upper(), sub_font, sub_tr)
        sub_h = _text_height(d, subtitle.upper(), sub_font)

    pre_font = pre_tr = None
    pre_h = 0
    if prefix:
        pre_font, pre_tr = _fit(d, prefix.upper(), fonts["sans"],
                                W * 0.5, H * 0.05,
                                tracking_em=0.7, start=80, min_size=10)
        pre_h = _text_height(d, prefix.upper(), pre_font)

    # --- Layout block ---
    gap = H * 0.035
    rule_w = max(main_w, sub_w) + W * 0.05
    rule_w = min(rule_w, W * 0.86)
    rule_thickness = max(1, int(H * 0.004))

    block_h = main_h
    if subtitle: block_h += gap + sub_h
    if prefix:   block_h += gap + pre_h

    if placement == "top":
        top = H * 0.10
    elif placement == "center":
        top = (H - block_h) / 2
    else:  # bottom
        top = H - H * 0.11 - block_h

    cx = W / 2
    y = top

    # Prefix
    if prefix and pre_font:
        _draw_centered_shadow(d, cx, y + pre_h / 2, prefix.upper(),
                              pre_font, pre_tr, palette, shadow=2, stroke_width=0)
        y += pre_h + gap * 0.7

    # Top rule
    ry = y + gap * 0.25
    d.line([(cx - rule_w / 2, ry), (cx + rule_w / 2, ry)],
           fill=palette["accent"], width=rule_thickness)
    y += gap

    # Main title
    _draw_centered_shadow(d, cx, y + main_h / 2, title.upper(),
                          main_font, main_tr, palette, shadow=3, stroke_width=2)
    y += main_h + gap * 0.55

    # Bottom rule
    ry = y - gap * 0.3
    d.line([(cx - rule_w / 2, ry), (cx + rule_w / 2, ry)],
           fill=palette["accent"], width=rule_thickness)
    y += gap * 0.7

    # Subtitle
    if subtitle and sub_font:
        _draw_centered_shadow(d, cx, y + sub_h / 2, subtitle.upper(),
                              sub_font, sub_tr, palette, shadow=2, stroke_width=1)
    return img


# ---------- 2. POSTER ----------
def _p_poster(W, H, title, subtitle, prefix, palette, fonts, placement):
    """Huge condensed caps anchored at the bottom, with a soft scrim."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Scrim: subtle dark gradient in the lower 55% so light text pops on any bg.
    scrim = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(scrim)
    y0 = int(H * 0.45)
    for i in range(y0, H):
        t = (i - y0) / max(1, H - y0 - 1)
        alpha = int(120 * (t ** 1.4))
        sd.line([(0, i), (W, i)], fill=(0, 0, 0, alpha))
    img.alpha_composite(scrim)

    # Fit huge title
    font, tr = _fit(d, title.upper(), fonts["condensed"],
                    W * 0.88, H * 0.42, tracking_em=0.04, start=400, min_size=24)
    title_h = _text_height(d, title.upper(), font)

    bottom_pad = H * 0.08
    title_cy = H - bottom_pad - title_h / 2

    # Optional subtitle above the title
    if subtitle:
        sub_is_ascii = _is_ascii(subtitle)
        sub_path = fonts["sans"] if sub_is_ascii else _cjk_font()
        sub_font, sub_tr = _fit(d, subtitle.upper(), sub_path,
                                W * 0.6, H * 0.07,
                                tracking_em=0.55 if sub_is_ascii else 0.12,
                                start=90, min_size=11)
        sub_h = _text_height(d, subtitle.upper(), sub_font)
        sub_cy = title_cy - title_h / 2 - H * 0.04 - sub_h / 2
        _draw_centered_shadow(d, W / 2, sub_cy, subtitle.upper(),
                              sub_font, sub_tr, palette, shadow=2, stroke_width=1)

    # Optional prefix below subtitle, above title
    if prefix:
        pre_font, pre_tr = _fit(d, prefix.upper(), fonts["sans"],
                                W * 0.5, H * 0.05, tracking_em=0.7,
                                start=80, min_size=10)
        pre_h = _text_height(d, prefix.upper(), pre_font)
        pre_cy = title_cy - title_h / 2 - H * 0.02 - pre_h / 2
        _draw_centered_shadow(d, W / 2, pre_cy, prefix.upper(),
                              pre_font, pre_tr, palette, shadow=2, stroke_width=0)

    # Title (with heavy shadow for legibility on bright backgrounds)
    _draw_centered_shadow(d, W / 2, title_cy, title.upper(), font, tr,
                          palette, shadow=max(4, int(H * 0.012)), stroke_width=3)
    return img


# ---------- 3. VINTAGE ----------
def _p_vintage(W, H, title, subtitle, prefix, palette, fonts, placement):
    """Diamond ornaments + italic serif name + tracked small caps."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    main_text = title.upper()
    main_font, main_tr = _fit(d, main_text, fonts["serif"],
                              W * 0.6, H * 0.16, tracking_em=0.22,
                              start=200, min_size=16)
    main_w = _tracked_width(d, main_text, main_font, main_tr)
    main_h = _text_height(d, main_text, main_font)

    sub_font = sub_tr = None
    sub_w = sub_h = 0
    if subtitle:
        sub_is_ascii = _is_ascii(subtitle)
        sub_path = fonts["serif_reg"] if sub_is_ascii else _cjk_font()
        sub_font, sub_tr = _fit(d, subtitle.upper(), sub_path,
                                W * 0.5, H * 0.07,
                                tracking_em=0.5 if sub_is_ascii else 0.12,
                                start=100, min_size=11)
        sub_w = _tracked_width(d, subtitle.upper(), sub_font, sub_tr)
        sub_h = _text_height(d, subtitle.upper(), sub_font)

    gap = H * 0.045
    line_w = max(main_w, sub_w) * 0.55 + W * 0.06

    block_h = main_h + gap + (sub_h + gap if subtitle else 0)

    if placement == "top":
        top = H * 0.10
    elif placement == "center":
        top = (H - block_h) / 2
    else:
        top = H - H * 0.11 - block_h

    cx = W / 2
    y = top

    # --- Ornament row above the name ---
    ornament_y = y - gap * 0.4
    _draw_ornament_row(d, cx, ornament_y, line_w,
                       palette["accent"], size=max(6, int(H * 0.014)),
                       thickness=max(1, int(H * 0.0035)))

    # --- Main name ---
    _draw_centered_shadow(d, cx, y + main_h / 2, main_text,
                          main_font, main_tr, palette, shadow=2, stroke_width=2)
    y += main_h

    # --- Ornament row below the name ---
    ornament_y = y + gap * 0.55
    _draw_ornament_row(d, cx, ornament_y, line_w,
                       palette["accent"], size=max(6, int(H * 0.014)),
                       thickness=max(1, int(H * 0.0035)))
    y += gap

    # --- Subtitle ---
    if subtitle and sub_font:
        _draw_centered_shadow(d, cx, y + sub_h / 2, subtitle.upper(),
                              sub_font, sub_tr, palette, shadow=2, stroke_width=1)
    return img


def _draw_ornament_row(d, cx, y, half_width, color, size=8, thickness=2):
    """Thin line —◆— line with a diamond in the middle."""
    left = cx - half_width
    right = cx + half_width
    d.line([(left, y), (cx - size - 8, y)], fill=color, width=thickness)
    d.line([(cx + size + 8, y), (right, y)], fill=color, width=thickness)
    # diamond
    d.polygon([(cx, y - size), (cx + size, y),
               (cx, y + size), (cx - size, y)], fill=color)


# ---------- 4. STAMP ----------
def _p_stamp(W, H, title, subtitle, prefix, palette, fonts, placement):
    """Postage stamp in a corner, perforated edges."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    side = int(min(W, H) * 0.42)
    pad = int(min(W, H) * 0.06)

    if placement in ("tl", "tr"):
        sx, sy = (pad, pad) if placement == "tl" else (W - side - pad, pad)
    elif placement in ("bl", "br"):
        sx, sy = (pad, H - side - pad) if placement == "bl" else (W - side - pad, H - side - pad)
    else:
        sx, sy = W - side - pad, H - side - pad

    # --- Drop shadow behind the stamp ---
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        (sx + 6, sy + 8, sx + side + 6, sy + side + 8),
        radius=int(side * 0.05), fill=(0, 0, 0, 140))
    shadow = shadow.filter(ImageFilter.GaussianBlur(8))
    img.alpha_composite(shadow)

    # --- Stamp layer (built separately so we can punch perforations) ---
    stamp = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    sd = ImageDraw.Draw(stamp)

    # Off-white paper
    sd.rectangle((0, 0, side, side), fill=(250, 247, 240))

    # Thin inner frame
    inset = int(side * 0.09)
    frame_th = max(2, int(side * 0.012))
    sd.rectangle((inset, inset, side - inset, side - inset),
                 outline=palette["band"], width=frame_th)

    # Tiny top text ("POSTCARD" style label)
    top_label = (prefix or "POSTCARD").upper()
    top_font, top_tr = _fit(sd, top_label, fonts["sans"],
                            side * 0.65, side * 0.06,
                            tracking_em=0.6, start=60, min_size=8)
    top_h = _text_height(sd, top_label, top_font)
    _draw_centered(sd, side / 2, inset + top_h * 0.9, top_label,
                   top_font, top_tr, palette["band"])

    # Main location name (fitted into the stamp center)
    inner_w = side * 0.68
    inner_h = side * 0.28
    main_font, main_tr = _fit(sd, title.upper(), fonts["serif"],
                              inner_w, inner_h, tracking_em=0.15,
                              start=120, min_size=14)
    _draw_centered(sd, side / 2, side * 0.44, title.upper(),
                   main_font, main_tr, palette["band"])

    # Subtitle
    if subtitle:
        sub_is_ascii = _is_ascii(subtitle)
        sub_path = fonts["serif_reg"] if sub_is_ascii else _cjk_font()
        sub_font, sub_tr = _fit(sd, subtitle.upper(), sub_path,
                                inner_w, side * 0.10,
                                tracking_em=0.45 if sub_is_ascii else 0.1,
                                start=70, min_size=9)
        _draw_centered(sd, side / 2, side * 0.63, subtitle.upper(),
                       sub_font, sub_tr, palette["band"])

    # Small accent rule
    rule_y = side * 0.72
    sd.line([(side * 0.28, rule_y), (side * 0.72, rule_y)],
            fill=palette["accent"], width=max(1, int(side * 0.008)))

    # --- Punch perforations into alpha ---
    mask = Image.new("L", (side, side), 255)
    md = ImageDraw.Draw(mask)
    perf_r = max(4, int(side * 0.022))
    step = max(10, int(side * 0.08))
    for x in range(step // 2, side, step):
        md.ellipse((x - perf_r, -perf_r, x + perf_r, perf_r), fill=0)
        md.ellipse((x - perf_r, side - perf_r, x + perf_r, side + perf_r), fill=0)
    for y in range(step // 2, side, step):
        md.ellipse((-perf_r, y - perf_r, perf_r, y + perf_r), fill=0)
        md.ellipse((side - perf_r, y - perf_r, side + perf_r, y + perf_r), fill=0)

    stamp.putalpha(mask)
    img.alpha_composite(stamp, (sx, sy))
    return img


# ---------- 5. MINIMAL ----------
def _p_minimal(W, H, title, subtitle, prefix, palette, fonts, placement):
    """Single tracked line near the bottom edge, plus optional tiny rule."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    text = title.upper()
    font, tr = _fit(d, text, fonts["sans"], W * 0.55, H * 0.055,
                    tracking_em=0.6, start=100, min_size=11)
    tw = _tracked_width(d, text, font, tr)
    th = _text_height(d, text, font)

    # Optional small vertical rule above the text
    rule_w = max(20, int(tw * 0.14))
    ry = H - H * 0.06 - th - H * 0.045
    d.line([(W / 2, ry), (W / 2, ry + H * 0.028)],
           fill=palette["accent"], width=max(1, int(H * 0.004)))

    cy = H - H * 0.075 - th / 2
    _draw_centered_shadow(d, W / 2, cy, text, font, tr, palette,
                          shadow=2, stroke_width=1)

    if subtitle:
        sub_is_ascii = _is_ascii(subtitle)
        sub_path = fonts["sans"] if sub_is_ascii else _cjk_font()
        sub_font, sub_tr = _fit(d, subtitle.upper(), sub_path,
                                W * 0.5, H * 0.04,
                                tracking_em=0.5 if sub_is_ascii else 0.1,
                                start=70, min_size=9)
        sub_h = _text_height(d, subtitle.upper(), sub_font)
        _draw_centered_shadow(d, W / 2, H - H * 0.03 - sub_h / 2,
                              subtitle.upper(), sub_font, sub_tr,
                              palette, shadow=2, stroke_width=1)
    return img


# ---------- 6. BAND ----------
def _p_band(W, H, title, subtitle, prefix, palette, fonts, placement):
    """Solid color band across the bottom with bold text inside."""
    band_h = int(H * (0.20 if subtitle else 0.16))
    band_y = H - band_h

    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Accent top edge
    accent_th = max(3, int(H * 0.006))
    d.rectangle((0, band_y, W, band_y + accent_th),
                fill=palette["accent"])

    # Band
    d.rectangle((0, band_y + accent_th, W, H), fill=palette["band"])

    # Text inside
    inner_pad = int(H * 0.03)
    inner_w = W * 0.86
    inner_h = band_h - 2 * inner_pad - accent_th

    # If only title, make it big and bold
    if subtitle:
        title_box_h = inner_h * 0.55
        sub_box_h = inner_h * 0.32
        title_cy = band_y + accent_th + inner_pad + title_box_h * 0.55
        sub_cy = band_y + accent_th + inner_pad + title_box_h + inner_pad * 0.4 + sub_box_h / 2
    else:
        title_box_h = inner_h * 0.72
        title_cy = band_y + accent_th + (band_h - accent_th) / 2
        sub_cy = None

    # Title
    title_font, title_tr = _fit(d, title.upper(), fonts["condensed"],
                                inner_w, title_box_h, tracking_em=0.08,
                                start=300, min_size=18)
    _draw_centered(d, W / 2, title_cy, title.upper(),
                   title_font, title_tr, palette["text"])

    # Subtitle
    if subtitle and sub_cy:
        sub_is_ascii = _is_ascii(subtitle)
        sub_path = fonts["sans"] if sub_is_ascii else _cjk_font()
        sub_font, sub_tr = _fit(d, subtitle.upper(), sub_path,
                                inner_w * 0.8, sub_box_h,
                                tracking_em=0.55 if sub_is_ascii else 0.12,
                                start=90, min_size=10)
        _draw_centered(d, W / 2, sub_cy, subtitle.upper(),
                       sub_font, sub_tr, palette["accent"])
    return img


# ---------- 7. LAYERED ----------
def _p_layered(W, H, title, subtitle, prefix, palette, fonts, placement):
    """Oversized local script behind, English title in front."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    cx = W / 2
    if placement == "top":
        cy = H * 0.28
    elif placement == "center":
        cy = H / 2
    else:
        cy = H - H * 0.28

    # --- Huge ghost layer behind (subtitle if CJK, else script version) ---
    if subtitle and not _is_ascii(subtitle):
        ghost_text = subtitle
        ghost_path = _cjk_font()
        ghost_font, ghost_tr = _fit(d, ghost_text, ghost_path,
                                    W * 0.75, H * 0.75,
                                    tracking_em=0.0, start=500, min_size=40)
    else:
        ghost_text = title.lower()
        ghost_path = fonts["script"]
        ghost_font, ghost_tr = _fit(d, ghost_text, ghost_path,
                                    W * 0.78, H * 0.62,
                                    tracking_em=0.0, start=400, min_size=40)

    ghost_h = _text_height(d, ghost_text, ghost_font)
    ghost_bbox = d.textbbox((0, 0), ghost_text, font=ghost_font)
    ghost_w = _tracked_width(d, ghost_text, ghost_font, ghost_tr)
    ghost_x = cx - ghost_w / 2
    ghost_y = cy - ghost_h / 2 - ghost_bbox[1]

    # Draw ghost into a separate layer so we can apply reduced opacity
    ghost = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(ghost)
    _draw_tracked(gd, ghost_x, ghost_y, ghost_text, ghost_font, ghost_tr,
                  palette["text"] + (255,))
    # Fade ghost to ~35% opacity
    a = ghost.getchannel("A").point(lambda p: int(p * 0.35))
    ghost.putalpha(a)
    img.alpha_composite(ghost)

    # --- Foreground: English title ---
    title_text = title.upper()
    title_font, title_tr = _fit(d, title_text, fonts["serif"],
                                W * 0.55, H * 0.14,
                                tracking_em=0.22, start=180, min_size=14)
    _draw_centered_shadow(d, cx, cy, title_text, title_font, title_tr,
                          palette, shadow=3, stroke_width=2)

    # --- Subtitle below (if it wasn't used as the ghost) ---
    if subtitle and _is_ascii(subtitle):
        sub_font, sub_tr = _fit(d, subtitle.upper(), fonts["sans"],
                                W * 0.4, H * 0.05,
                                tracking_em=0.55, start=80, min_size=10)
        sub_h = _text_height(d, subtitle.upper(), sub_font)
        _draw_centered_shadow(d, cx, cy + H * 0.11 + sub_h / 2,
                              subtitle.upper(), sub_font, sub_tr,
                              palette, shadow=2, stroke_width=1)

    # --- Prefix above ---
    if prefix:
        pre_font, pre_tr = _fit(d, prefix.upper(), fonts["sans"],
                                W * 0.4, H * 0.045,
                                tracking_em=0.7, start=70, min_size=9)
        pre_h = _text_height(d, prefix.upper(), pre_font)
        _draw_centered_shadow(d, cx, cy - H * 0.11 - pre_h / 2,
                              prefix.upper(), pre_font, pre_tr,
                              palette, shadow=2, stroke_width=0)
    return img


# ---------- 8. POLAROID ----------
def _p_polaroid(W, H, title, subtitle, prefix, palette, fonts, placement):
    """Cream strip at the bottom, marker-style caption."""
    strip_h = int(H * (0.24 if subtitle else 0.20))
    strip_y = H - strip_h

    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Soft shadow above the strip
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rectangle(
        (0, strip_y - 8, W, strip_y + 4), fill=(0, 0, 0, 90))
    shadow = shadow.filter(ImageFilter.GaussianBlur(6))
    img.alpha_composite(shadow)

    # Strip (cream)
    d.rectangle((0, strip_y, W, H), fill=(250, 246, 234))
    # Thin accent line at top of strip
    d.rectangle((0, strip_y, W, strip_y + max(2, int(H * 0.004))),
                fill=palette["accent"])

    # Main caption
    cap_font, cap_tr = _fit(d, title, fonts["marker"],
                            W * 0.78, strip_h * 0.42,
                            tracking_em=0.02, start=220, min_size=18)
    cap_h = _text_height(d, title, cap_font)
    if subtitle:
        cap_cy = strip_y + strip_h * 0.30 + cap_h / 2
    else:
        cap_cy = strip_y + strip_h / 2

    _draw_centered(d, W / 2, cap_cy, title, cap_font, cap_tr, palette["band"])

    # Subtitle
    if subtitle:
        sub_is_ascii = _is_ascii(subtitle)
        sub_path = fonts["sans"] if sub_is_ascii else _cjk_font()
        sub_font, sub_tr = _fit(d, subtitle.upper(), sub_path,
                                W * 0.6, strip_h * 0.22,
                                tracking_em=0.55 if sub_is_ascii else 0.12,
                                start=80, min_size=10)
        _draw_centered(d, W / 2, strip_y + strip_h * 0.72,
                       subtitle.upper(), sub_font, sub_tr, palette["band"])
    return img


# =============================================================
#  MAIN
# =============================================================
_PRESET_FNS = {
    "editorial": _p_editorial,
    "poster":    _p_poster,
    "vintage":   _p_vintage,
    "stamp":     _p_stamp,
    "minimal":   _p_minimal,
    "band":      _p_band,
    "layered":   _p_layered,
    "polaroid":  _p_polaroid,
}


def postcard_title(
    place_name,
    output_path=None,
    canvas_size=(1200, 500),
    seed=None,
    preset="editorial",
    palette="auto",
    placement="auto",
    background=None,
    composite_background=False,
    subtitle=None,
    subtitle_font=None,
    prefix=None,
):
    """
    Draw a tourist-postcard location title.

    Parameters
    ----------
    place_name   : str  — main title, e.g. "Kyoto"
    preset       : one of "editorial", "poster", "vintage", "stamp",
                   "minimal", "band", "layered", "polaroid"
    palette      : "auto" or a key from PALETTES
    placement    : "auto", or "top"/"center"/"bottom" for text presets,
                   or "tl"/"tr"/"bl"/"br" for badge presets
    background   : PIL.Image, path str, or None
    subtitle     : str  — secondary line, e.g. "JAPAN" or "京都"
    prefix       : str  — e.g. "GREETINGS FROM"

    Returns
    -------
    PIL.Image (RGBA). If composite_background=True and background was
    given, the output is the full postcard. Otherwise it is a transparent
    overlay.
    """
    if seed is not None:
        random.seed(seed)

    place_name = (place_name or "").strip()
    if not place_name:
        raise ValueError("place_name cannot be empty")
    if preset not in _PRESET_FNS:
        raise ValueError(f"unknown preset '{preset}'. "
                         f"Choose from {sorted(_PRESET_FNS)}")

    W, H = canvas_size

    # --- Load background -------------------------------------------------
    bg_img = None
    if background is not None:
        if isinstance(background, Image.Image):
            bg_img = background
        elif isinstance(background, str):
            bg_img = Image.open(background)
        if bg_img is not None and bg_img.mode != "RGB":
            bg_img = bg_img.convert("RGB")

    # --- Auto placement --------------------------------------------------
    bg_info = None
    if bg_img is not None:
        bg_info = analyze_background(bg_img, canvas_size)

    if placement == "auto":
        if bg_info is not None:
            placement = (bg_info["position"] if preset in TEXT_PRESETS
                         else bg_info["corner"])
        else:
            placement = "bottom" if preset in TEXT_PRESETS else "br"

    # --- Palette ---------------------------------------------------------
    bg_lum = None
    if bg_info is not None:
        bg_lum = (bg_info["corner_luminance"] if preset in BADGE_PRESETS
                  else bg_info["luminance"])
    pal = pick_palette(palette, bg_lum=bg_lum)

    # --- Fonts -----------------------------------------------------------
    fonts = load_fonts()

    # --- Draw preset -----------------------------------------------------
    overlay = _PRESET_FNS[preset](
        W, H,
        title=place_name,
        subtitle=subtitle,
        prefix=prefix,
        palette=pal,
        fonts=fonts,
        placement=placement,
    )

    # --- Composite -------------------------------------------------------
    if composite_background and bg_img is not None:
        base = bg_img.resize((W, H), Image.Resampling.LANCZOS).convert("RGBA")
        base.alpha_composite(overlay)
        final = base
    else:
        final = overlay

    if output_path:
        final.save(output_path)
    return final