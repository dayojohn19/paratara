from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops, ImageStat
import random
import os
import colorsys


# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
TITLE_SCALE = 0.64

# Minimum contrast ratio between text fill and background for readability.
MIN_BG_CONTRAST = 3.0
# Minimum contrast between fill and outline.
MIN_OUTLINE_CONTRAST = 4.0


# ---------------------------------------------------------------------------
# FONT HELPERS
# ---------------------------------------------------------------------------
def _system_font_fallbacks():
    return [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "DejaVuSans-Bold.ttf",
        "DejaVuSans.ttf",
    ]


def find_font(bold=False, mood=None):
    font_sets = {
        "display": [
            "garden/assets/fonts/Anton/Anton-Regular.ttf",
            "garden/assets/fonts/ArchivoBlack/ArchivoBlack-Regular.ttf",
            "garden/assets/fonts/BebasNeue/BebasNeue-Regular.ttf",
            "garden/assets/fonts/Righteous/Righteous-Regular.ttf",
            "garden/assets/fonts/Audiowide/Audiowide-Regular.ttf",
            "garden/assets/fonts/Monoton/Monoton-Regular.ttf",
            "garden/assets/fonts/Oswald/Oswald-Bold.ttf",
            "garden/assets/fonts/Staatliches/Staatliches-Regular.ttf",
            "garden/assets/fonts/AbrilFatface/AbrilFatface-Regular.ttf",
        ],
        "script": [
            "garden/assets/fonts/GreatVibes/GreatVibes-Regular.ttf",
            "garden/assets/fonts/Pacifico/Pacifico-Regular.ttf",
            "garden/assets/fonts/Lobster/Lobster-Regular.ttf",
            "garden/assets/fonts/DancingScript/DancingScript-Regular.ttf",
            "garden/assets/fonts/DancingScript/DancingScript-Bold.ttf",
            "garden/assets/fonts/Sacramento/Sacramento-Regular.ttf",
        ],
        "hand": [
            "garden/assets/fonts/PermanentMarker/PermanentMarker-Regular.ttf",
            "garden/assets/fonts/ShadowsIntoLight/ShadowsIntoLight-Regular.ttf",
            "garden/assets/fonts/Caveat/Caveat-Regular.ttf",
            "garden/assets/fonts/Caveat/Caveat-Bold.ttf",
            "garden/assets/fonts/RockSalt/RockSalt-Regular.ttf",
        ],
        "rounded": [
            "garden/assets/fonts/BubblegumSans/BubblegumSans-Regular.ttf",
            "garden/assets/fonts/FredokaOne/FredokaOne-Regular.ttf",
            "garden/assets/fonts/Baloo2/Baloo2-Regular.ttf",
            "garden/assets/fonts/Baloo2/Baloo2-Bold.ttf",
            "garden/assets/fonts/Comfortaa/Comfortaa-Regular.ttf",
            "garden/assets/fonts/Comfortaa/Comfortaa-Bold.ttf",
            "garden/assets/fonts/PlayfairDisplay/PlayfairDisplay-Regular.ttf",
            "garden/assets/fonts/PlayfairDisplay/PlayfairDisplay-Bold.ttf",
            "garden/assets/fonts/Cinzel/Cinzel-Regular.ttf",
            "garden/assets/fonts/Cinzel/Cinzel-Bold.ttf",
        ],
        "sans_clean": [
            "garden/assets/fonts/dmsans/DMSans[opsz,wght].ttf",
            "garden/assets/fonts/inter/Inter[slnt,wght].ttf",
            "garden/assets/fonts/helvetica-255/Helvetica-Bold.ttf",
            "garden/assets/fonts/helvetica-255/helvetica-rounded-bold-5871d05ead8de.otf",
            "garden/assets/fonts/dejavu-sans/DejaVuSans-Bold.ttf",
            "garden/assets/fonts/dejavu-sans/DejaVuSans.ttf",
        ],
    }

    candidates = []
    if mood:
        candidates += font_sets.get(mood, [])

    if bold:
        candidates += font_sets["display"] + font_sets["rounded"]
    else:
        candidates += font_sets["hand"] + font_sets["script"]

    candidates += font_sets["sans_clean"]

    existing = [p for p in candidates if p and os.path.exists(p)]
    if existing:
        return random.choice(existing)

    for path in _system_font_fallbacks():
        if os.path.exists(path):
            try:
                ImageFont.truetype(path, 20)
                return path
            except OSError:
                continue

    raise RuntimeError(
        "No usable font found. Run download_fonts.py to fetch the Google "
        "Fonts, or install a system font (DejaVu / Arial / Liberation)."
    )


def find_font_from_candidates(candidates, randomize=True):
    existing = [p for p in candidates if p and os.path.exists(p)]
    if not existing:
        return None
    return random.choice(existing) if randomize else existing[0]


def _pick_subtitle_font(explicit_path, place_name):
    """Pick a font that likely supports the subtitle script."""
    if explicit_path and os.path.exists(explicit_path):
        return explicit_path

    # CJK / Japanese / Korean / Arabic / Cyrillic / Thai common paths.
    script_candidates = [
        # Noto family (best cross-script coverage)
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansJP-Regular.otf",
        "/usr/share/fonts/truetype/noto/NotoSansKR-Regular.otf",
        "/usr/share/fonts/truetype/noto/NotoSansSC-Regular.otf",
        "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansThai-Regular.ttf",
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/YuGothR.ttc",
        "C:/Windows/Fonts/malgun.ttf",
        # Latin fallbacks
        "garden/assets/fonts/dmsans/DMSans[opsz,wght].ttf",
        "garden/assets/fonts/inter/Inter[slnt,wght].ttf",
        "garden/assets/fonts/dejavu-sans/DejaVuSans-Bold.ttf",
    ]
    return find_font_from_candidates(script_candidates, randomize=False) or \
        find_font_from_candidates(_system_font_fallbacks(), randomize=False)


# ---------------------------------------------------------------------------
# TEXT MEASUREMENT
# ---------------------------------------------------------------------------
def text_bbox(draw, text, font, stroke_width=0):
    return draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)


def fit_font(draw, text, font_path, max_width, max_height, start_size,
             min_size=18, stroke_width=0):
    size = start_size
    while size >= min_size:
        font = ImageFont.truetype(font_path, size)
        bbox = text_bbox(draw, text, font, stroke_width)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        if w <= max_width and h <= max_height:
            return font
        size -= 3
    return ImageFont.truetype(font_path, min_size)


def featured_word_bottom(draw, text, font, stroke_width=3, shadow_depth=14):
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    return bbox[3] + shadow_depth


# ---------------------------------------------------------------------------
# COLOR HELPERS
# ---------------------------------------------------------------------------
def clamp_rgb(rgb):
    return tuple(max(0, min(255, int(v))) for v in rgb)


def mix_rgb(rgb_a, rgb_b, ratio):
    return clamp_rgb((
        rgb_a[0] * (1.0 - ratio) + rgb_b[0] * ratio,
        rgb_a[1] * (1.0 - ratio) + rgb_b[1] * ratio,
        rgb_a[2] * (1.0 - ratio) + rgb_b[2] * ratio,
    ))


def rgba(rgb, alpha=255):
    return tuple(rgb) + (alpha,)


def make_wordart_palette(fill_rgb, outline_rgb, accent_rgb=None):
    if accent_rgb is None:
        accent_rgb = mix_rgb(fill_rgb, outline_rgb, 0.45)

    shadow_rgb = mix_rgb(fill_rgb, (8, 12, 18), 0.42)
    highlight_rgb = mix_rgb((255, 255, 255), fill_rgb, 0.3)
    band_rgb = mix_rgb(accent_rgb, outline_rgb, 0.28)

    return {
        "main": rgba(fill_rgb),
        "outline": rgba(outline_rgb),
        "shadow": rgba(shadow_rgb, 155),
        "accent": rgba(accent_rgb),
        "highlight": rgba(highlight_rgb, 88),
        "band": rgba(band_rgb, 42),
        "pattern": rgba(accent_rgb, 56),
    }


def _hsl_to_rgb(h, s, l):
    h = h % 1.0
    s = max(0.0, min(1.0, s))
    l = max(0.0, min(1.0, l))
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return (int(round(r * 255)), int(round(g * 255)), int(round(b * 255)))


def _relative_luminance(rgb):
    def lin(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def contrast_ratio(rgb_a, rgb_b):
    la, lb = _relative_luminance(rgb_a), _relative_luminance(rgb_b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def _ensure_contrast(fill, outline, min_ratio=3.6):
    if contrast_ratio(fill, outline) >= min_ratio:
        return outline

    white = (250, 250, 252)
    black = (10, 10, 14)
    target = white if contrast_ratio(fill, white) >= contrast_ratio(fill, black) else black

    for i in range(1, 21):
        t = i / 20.0
        cand = clamp_rgb(tuple(outline[k] * (1 - t) + target[k] * t for k in range(3)))
        if contrast_ratio(fill, cand) >= min_ratio:
            return cand
    return target


_SCHEMES = {
    "complementary": 0.50,
    "analogous":     0.083,
    "triad":         0.333,
    "split":         0.416,
    "monochrome":    0.00,
    "tetrad":        0.25,
}


def _palette_from_hue(hue, sat=0.75, fill_light=0.42, scheme="complementary",
                      outline_dark=True, accent_light=0.55):
    acc_h = hue + _SCHEMES.get(scheme, 0.5)
    fill = _hsl_to_rgb(hue, sat, fill_light)
    accent = _hsl_to_rgb(acc_h, min(1.0, sat * 1.15), accent_light)

    if outline_dark:
        outline = _hsl_to_rgb(hue, min(1.0, sat * 0.9), 0.12)
    else:
        outline = _hsl_to_rgb(hue, min(1.0, sat * 0.4), 0.96)

    outline = _ensure_contrast(fill, outline, min_ratio=4.0)
    return fill, outline, accent


_PALETTE_RECIPES = [
    ("royal_navy",      0.61, 0.72, 0.28, "complementary", True),
    ("sunset_coral",    0.03, 0.85, 0.55, "analogous",     True),
    ("tropical_teal",   0.48, 0.78, 0.42, "triad",         True),
    ("bubblegum_pop",   0.92, 0.85, 0.72, "split",         True),
    ("forest_emerald",  0.38, 0.75, 0.30, "analogous",     True),
    ("sakura_pink",     0.94, 0.55, 0.78, "analogous",     True),
    ("deep_plum",       0.80, 0.62, 0.30, "triad",         True),
    ("mustard_vintage", 0.12, 0.78, 0.55, "complementary", True),
    ("ocean_depth",     0.55, 0.75, 0.30, "analogous",     True),
    ("lavender_mist",   0.72, 0.52, 0.75, "split",         True),
    ("espresso",        0.07, 0.55, 0.22, "analogous",     False),
    ("mint_fresh",      0.42, 0.60, 0.72, "analogous",     True),
    ("midnight_neon",   0.68, 0.90, 0.22, "split",         True),
    ("peach_cream",     0.06, 0.72, 0.78, "analogous",     True),
    ("arctic_ice",      0.55, 0.35, 0.82, "complementary", False),
    ("crimson_royal",   0.98, 0.75, 0.38, "complementary", True),
    ("citrus_splash",   0.16, 0.90, 0.55, "triad",         True),
    ("violet_dream",    0.78, 0.72, 0.55, "split",         True),
    ("slate_modern",    0.58, 0.35, 0.35, "analogous",     True),
    ("rose_gold",       0.03, 0.45, 0.72, "analogous",     True),
    ("caribbean",       0.46, 0.82, 0.46, "complementary", True),
    ("candy_grape",     0.76, 0.78, 0.68, "split",         True),
    ("retro_orange",    0.08, 0.88, 0.52, "triad",         True),
]


_NAME_HUE_HINTS = {
    "beach":    [0.48, 0.08, 0.55],
    "ocean":    [0.55, 0.48],
    "sea":      [0.55, 0.48],
    "bay":      [0.55, 0.48],
    "coast":    [0.52, 0.06],
    "harbor":   [0.55, 0.10],
    "island":   [0.48, 0.12, 0.08],
    "tropic":   [0.42, 0.08],
    "palm":     [0.35, 0.48],
    "mountain": [0.35, 0.58, 0.10],
    "forest":   [0.35, 0.38],
    "valley":   [0.35, 0.10],
    "lake":     [0.55, 0.42],
    "river":    [0.50, 0.42],
    "desert":   [0.09, 0.05],
    "canyon":   [0.06, 0.09],
    "sunset":   [0.02, 0.05, 0.85],
    "sunrise":  [0.10, 0.05],
    "spring":   [0.32, 0.85],
    "summer":   [0.14, 0.48, 0.08],
    "autumn":   [0.06, 0.09, 0.03],
    "fall":     [0.06, 0.09],
    "winter":   [0.55, 0.62],
    "snow":     [0.55, 0.60],
    "ice":      [0.55, 0.60],
    "garden":   [0.35, 0.85, 0.42],
    "rose":     [0.95, 0.88],
    "cherry":   [0.98, 0.02],
    "golden":   [0.11, 0.09],
    "gold":     [0.11],
    "silver":   [0.58],
    "emerald":  [0.38],
    "ruby":     [0.98],
    "sapphire": [0.61],
    "midnight": [0.68, 0.62],
    "moon":     [0.58, 0.62],
    "star":     [0.58, 0.68],
    "fire":     [0.02, 0.06],
    "coral":    [0.03, 0.05],
    "peach":    [0.06],
    "mint":     [0.42],
    "lavender": [0.75],
    "violet":   [0.78],
    "purple":   [0.78],
    "city":     [0.62, 0.72, 0.00],
    "town":     [0.10, 0.58],
    "village":  [0.10, 0.35],
}


_STYLE_SCHEME_BIAS = {
    "pop_bubble":              ("split", "analogous", "triad"),
    "script_luxe":             ("analogous", "complementary", "monochrome"),
    "retro_condensed":         ("triad", "complementary", "split"),
    "thin_art_deco":           ("monochrome", "complementary", "analogous"),
    "giant_block":             ("complementary", "triad", "split"),
    "shadow_poster":           ("complementary", "split", "analogous"),
    "signature_mix":           ("analogous", "monochrome"),
    "big_first_small_rest":    ("complementary", "analogous", "split"),
    "wide_first_script_rest":  ("analogous", "complementary"),
}


def _collect_hue_hints(place_name):
    if not place_name:
        return []
    hints = []
    for raw in place_name.lower().split():
        word = raw.strip(".,!?'\"-")
        if not word:
            continue
        if word in _NAME_HUE_HINTS:
            hints.extend(_NAME_HUE_HINTS[word])
            continue
        for key, hues in _NAME_HUE_HINTS.items():
            if key in word:
                hints.extend(hues)
    return hints


def _smart_palettes(place_name=None, style=None):
    schemes = _STYLE_SCHEME_BIAS.get(style, ("complementary", "analogous", "split", "triad"))
    hints = _collect_hue_hints(place_name)
    palettes = []
    used_hues = []

    def _add(hue, scheme, sat, light, dark_outline, accent_light=0.55):
        fill, outline, accent = _palette_from_hue(
            hue, sat, light, scheme, dark_outline, accent_light
        )
        palettes.append(make_wordart_palette(fill, outline, accent))
        used_hues.append(hue)

    for hint_h in hints:
        hue = hint_h + random.uniform(-0.035, 0.035)
        _add(
            hue,
            random.choice(schemes),
            sat=random.uniform(0.65, 0.92),
            light=random.uniform(0.34, 0.58),
            dark_outline=random.random() < 0.8,
            accent_light=random.uniform(0.48, 0.62),
        )

    pool = list(_PALETTE_RECIPES)
    random.shuffle(pool)
    for _name, hue, sat, light, scheme, dark in pool:
        too_close = any(abs((hue - u + 0.5) % 1.0 - 0.5) < 0.05 for u in used_hues)
        if too_close:
            continue
        _add(hue, scheme, sat, light, dark)
        if len(palettes) >= 10:
            break

    if not palettes:
        palettes.append(make_wordart_palette((20, 40, 70), (250, 250, 252)))
    return palettes


def build_wordart_palettes(mode="smart", place_name=None, style=None):
    chrome = [
        make_wordart_palette((224, 232, 244), (34, 46, 66), (116, 140, 178)),
        make_wordart_palette((242, 245, 250), (28, 36, 52), (152, 166, 188)),
        make_wordart_palette((210, 220, 236), (20, 30, 46), (100, 120, 152)),
        make_wordart_palette((60, 70, 92), (235, 240, 250), (160, 178, 205)),
    ]
    neon = [
        make_wordart_palette((76, 255, 235), (12, 35, 50), (7, 214, 255)),
        make_wordart_palette((255, 94, 214), (48, 10, 44), (255, 170, 70)),
        make_wordart_palette((178, 255, 82), (22, 46, 20), (69, 230, 160)),
        make_wordart_palette((255, 230, 90), (40, 20, 0), (255, 90, 180)),
        make_wordart_palette((140, 100, 255), (20, 8, 50), (255, 100, 220)),
    ]
    candy = [
        make_wordart_palette((255, 189, 210), (86, 41, 58), (255, 126, 170)),
        make_wordart_palette((255, 216, 166), (95, 56, 32), (255, 149, 95)),
        make_wordart_palette((194, 232, 255), (44, 70, 96), (129, 178, 255)),
        make_wordart_palette((220, 200, 255), (72, 48, 100), (180, 140, 255)),
        make_wordart_palette((190, 255, 210), (36, 80, 56), (120, 230, 160)),
    ]
    metallic_gold = [
        make_wordart_palette((245, 214, 120), (66, 45, 14), (222, 170, 58)),
        make_wordart_palette((255, 226, 142), (74, 52, 18), (228, 183, 80)),
        make_wordart_palette((232, 191, 98), (58, 39, 12), (209, 150, 52)),
        make_wordart_palette((210, 170, 70), (40, 26, 8), (245, 215, 130)),
    ]

    if mode == "chrome":
        return chrome
    if mode == "neon":
        return neon
    if mode == "candy":
        return candy
    if mode == "metallic_gold":
        return metallic_gold

    return _smart_palettes(place_name=place_name, style=style)


# ---------------------------------------------------------------------------
# ADAPTIVE CONTRAST (NEW)
# ---------------------------------------------------------------------------
def adapt_palette_to_background(palette, bg_luminance):
    """Nudge palette fill/outline so text stays readable over a background.

    bg_luminance: 0.0 (black) to 1.0 (white).
    """
    if bg_luminance is None:
        return palette

    bg_rgb = (int(bg_luminance * 255),) * 3
    main_rgb = palette["main"][:3]
    outline_rgb = palette["outline"][:3]
    accent_rgb = palette["accent"][:3]

    if contrast_ratio(main_rgb, bg_rgb) >= MIN_BG_CONTRAST:
        return palette

    # Decide which direction to push the fill.
    # If bg is bright, we need a darker fill. If dark, a brighter fill.
    if bg_luminance > 0.55:
        target = (15, 18, 28)
    else:
        target = (248, 246, 240)

    new_fill = main_rgb
    for t in (0.35, 0.55, 0.75, 0.9, 1.0):
        candidate = mix_rgb(main_rgb, target, t)
        if contrast_ratio(candidate, bg_rgb) >= MIN_BG_CONTRAST:
            new_fill = candidate
            break
    else:
        new_fill = target

    new_outline = _ensure_contrast(new_fill, outline_rgb, MIN_OUTLINE_CONTRAST)
    return make_wordart_palette(new_fill, new_outline, accent_rgb)


# ---------------------------------------------------------------------------
# BACKGROUND ANALYSIS (NEW — smart positioning)
# ---------------------------------------------------------------------------
def _band_busyness(gray, num_bands=5):
    """Return an edge-density score per horizontal band (0=clean, 1=busy)."""
    w, h = gray.size
    band_h = max(1, h // num_bands)
    scores = []
    for i in range(num_bands):
        y0 = i * band_h
        y1 = h if i == num_bands - 1 else y0 + band_h
        band = gray.crop((0, y0, w, y1))
        edges = band.filter(ImageFilter.FIND_EDGES)
        scores.append(ImageStat.Stat(edges).mean[0] / 255.0)
    return scores


def pick_smart_position(bg_img, canvas_size):
    """Choose 'top' | 'center' | 'bottom' based on where the bg is calmest.

    Postcards conventionally put the title at bottom or top, so we bias
    toward those when scores are close.
    """
    bg = bg_img.resize(canvas_size, Image.Resampling.LANCZOS).convert("L")
    scores = _band_busyness(bg, num_bands=5)

    top_score = min(scores[0], scores[1])
    center_score = scores[2]
    bottom_score = min(scores[3], scores[4])

    # Small bias: bottom is slightly preferred, then top, then center.
    weights = {"bottom": 0.00, "top": 0.02, "center": 0.04}
    ranked = sorted(
        [
            ("bottom", bottom_score + weights["bottom"]),
            ("top",    top_score + weights["top"]),
            ("center", center_score + weights["center"]),
        ],
        key=lambda x: x[1],
    )
    return ranked[0][0]


def sample_background_luminance(bg_img, canvas_size, position):
    """Average luminance in the region where the text will land."""
    bg = bg_img.resize(canvas_size, Image.Resampling.LANCZOS).convert("L")
    w, h = bg.size

    if position == "top":
        region = (0, 0, w, int(h * 0.45))
    elif position == "bottom":
        region = (0, int(h * 0.55), w, h)
    else:  # center
        region = (0, int(h * 0.25), w, int(h * 0.75))

    return ImageStat.Stat(bg.crop(region)).mean[0] / 255.0


# ---------------------------------------------------------------------------
# TEXT DRAWING
# ---------------------------------------------------------------------------
def spaced_text_width(draw, text, font, spacing=10, stroke_width=0):
    total = 0
    max_h = 0
    for char in text:
        bbox = draw.textbbox((0, 0), char, font=font, stroke_width=stroke_width)
        total += bbox[2] - bbox[0] + spacing
        max_h = max(max_h, bbox[3] - bbox[1])
    return max(0, total - spacing), max_h


def draw_spaced_text(draw, x, y, text, font, fill, spacing=10,
                     stroke_width=0, stroke_fill=None):
    for char in text:
        draw.text(
            (x, y), char, font=font, fill=fill,
            stroke_width=stroke_width, stroke_fill=stroke_fill,
        )
        bbox = draw.textbbox((0, 0), char, font=font, stroke_width=stroke_width)
        x += bbox[2] - bbox[0] + spacing


def draw_varied_spaced_text(draw, x, y, text, font, fill, spacing=10,
                            stroke_width=0, stroke_fill=None, wave=0):
    for i, char in enumerate(text):
        offset_y = int(wave * (1 if i % 2 == 0 else -1))
        draw.text(
            (x, y + offset_y), char, font=font, fill=fill,
            stroke_width=stroke_width, stroke_fill=stroke_fill,
        )
        bbox = draw.textbbox((0, 0), char, font=font, stroke_width=stroke_width)
        x += bbox[2] - bbox[0] + spacing + (i % 3)


def text_mask(size, x, y, text, font):
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).text((x, y), text, font=font, fill=255)
    return mask


def spaced_text_mask(size, x, y, text, font, spacing=10, wave=0, stroke_width=0):
    mask = Image.new("L", size, 0)
    d = ImageDraw.Draw(mask)
    for i, char in enumerate(text):
        offset_y = int(wave * (1 if i % 2 == 0 else -1))
        d.text((x, y + offset_y), char, font=font, fill=255,
               stroke_width=stroke_width, stroke_fill=255)
        bbox = d.textbbox((0, 0), char, font=font, stroke_width=stroke_width)
        x += bbox[2] - bbox[0] + spacing + (i % 3)
    return mask


def fill_mask_with_gradient(layer, mask, top_rgb, bottom_rgb):
    w, h = layer.size
    gradient_col = Image.new("RGBA", (1, h), (0, 0, 0, 0))
    for y_pos in range(h):
        ratio = y_pos / max(h - 1, 1)
        r = int(top_rgb[0] * (1 - ratio) + bottom_rgb[0] * ratio)
        g = int(top_rgb[1] * (1 - ratio) + bottom_rgb[1] * ratio)
        b = int(top_rgb[2] * (1 - ratio) + bottom_rgb[2] * ratio)
        gradient_col.putpixel((0, y_pos), (r, g, b, 255))
    gradient = gradient_col.resize((w, h), Image.Resampling.BICUBIC)
    gradient.putalpha(mask)
    layer.alpha_composite(gradient)


def apply_wordart_text(layer, fill_mask, stroke_mask, outer_mask, palette):
    depth_alpha = ImageChops.subtract(ImageChops.offset(stroke_mask, 7, 8), stroke_mask)
    depth = Image.new("RGBA", layer.size,
                      mix_rgb(palette["shadow"][:3], (0, 0, 0), 0.2) + (118,))
    depth.putalpha(ImageChops.multiply(depth.getchannel("A"), depth_alpha))
    depth = depth.filter(ImageFilter.GaussianBlur(1.2))
    layer.alpha_composite(depth)

    rim_mask = ImageChops.subtract(outer_mask, stroke_mask)
    rim = Image.new("RGBA", layer.size, palette["accent"])
    rim.putalpha(ImageChops.multiply(rim.getchannel("A"), rim_mask))
    layer.alpha_composite(rim)

    stroke_ring = ImageChops.subtract(stroke_mask, fill_mask)
    stroke = Image.new("RGBA", layer.size, palette["outline"])
    stroke.putalpha(ImageChops.multiply(stroke.getchannel("A"), stroke_ring))
    layer.alpha_composite(stroke)

    top_rgb = mix_rgb(palette["main"][:3], (255, 255, 255), 0.64)
    bottom_rgb = mix_rgb(palette["accent"][:3], (12, 20, 28), 0.22)
    fill_mask_with_gradient(layer, fill_mask, top_rgb, bottom_rgb)

    w, h = layer.size
    gloss_col = Image.new("RGBA", (1, h), (255, 255, 255, 0))
    for y_pos in range(h):
        ratio = y_pos / max(h - 1, 1)
        alpha = int((0.36 - ratio) / 0.36 * 122) if ratio <= 0.36 else 0
        gloss_col.putpixel((0, y_pos), (255, 255, 255, alpha))
    gloss = gloss_col.resize((w, h), Image.Resampling.BICUBIC)
    gloss.putalpha(ImageChops.multiply(gloss.getchannel("A"), fill_mask))
    layer.alpha_composite(gloss)


def add_text_sheen(layer, mask, bbox, opacity=82):
    sheen = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(sheen)
    x, y, w, h = bbox
    draw.rounded_rectangle(
        (x - 4, y + 2, x + w + 4, y + max(16, int(h * 0.32))),
        radius=max(10, int(h * 0.08)),
        fill=(255, 255, 255, opacity),
    )
    alpha = ImageChops.multiply(sheen.getchannel("A"), mask)
    sheen.putalpha(alpha)
    layer.alpha_composite(sheen)


def add_text_pattern(layer, mask, bbox, palette):
    pattern = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(pattern)
    x, y, w, h = bbox

    line_gap = max(12, int(h * 0.1))
    for y_pos in range(int(y - h * 0.05), int(y + h), line_gap):
        draw.line(
            (x - 20, y_pos + 10, x + w + 20, y_pos - 10),
            fill=palette["pattern"],
            width=max(2, int(h * 0.025)),
        )

    band_top = y + int(h * 0.46)
    band_bottom = y + int(h * 0.72)
    draw.rounded_rectangle(
        (x - 3, band_top, x + w + 3, band_bottom),
        radius=max(10, int(h * 0.08)),
        fill=palette["band"],
    )

    for ratio in (0.16, 0.82):
        cx = x + int(w * ratio)
        cy = y + int(h * 0.24)
        radius = max(3, int(h * 0.04))
        draw.ellipse(
            (cx - radius, cy - radius, cx + radius, cy + radius),
            fill=palette["highlight"],
        )

    alpha = ImageChops.multiply(pattern.getchannel("A"), mask)
    pattern.putalpha(alpha)
    layer.alpha_composite(pattern)


def draw_diamond(draw, cx, cy, size, fill):
    draw.polygon(
        [(cx, cy - size), (cx + size, cy), (cx, cy + size), (cx - size, cy)],
        fill=fill,
    )


def draw_first_name_ornaments(draw, x, y, w, h, palette):
    top = y - 20
    bottom = y + h + 22
    left = x - 24
    right = x + w + 24
    draw.line((left + 42, top, right - 42, top), fill=palette["accent"], width=3)
    draw.line((left + 60, bottom, right - 60, bottom), fill=palette["accent"], width=3)
    for cx in (left + 18, right - 18):
        draw.ellipse((cx - 8, top - 8, cx + 8, top + 8),
                     outline=palette["accent"], width=3)
        draw_diamond(draw, cx, bottom, 9, palette["accent"])
    mid_y = y + h // 2
    for cx in (left, right):
        draw.arc((cx - 20, mid_y - 22, cx + 20, mid_y + 22), 80, 280,
                 fill=palette["outline"], width=3)


def draw_featured_first_word(layer, x, y, text, font, palette, stroke_width=3,
                             shadow_depth=14):
    d = ImageDraw.Draw(layer)
    bbox = d.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]

    for off in (shadow_depth,
                int(shadow_depth * 0.65),
                int(shadow_depth * 0.35)):
        d.text(
            (x + off, y + off), text, font=font,
            fill=palette["shadow"], stroke_width=stroke_width,
            stroke_fill=palette["shadow"],
        )

    d.text(
        (x + 5, y - 4), text, font=font, fill=palette["accent"],
        stroke_width=max(1, stroke_width - 1), stroke_fill=palette["outline"],
    )

    fill_mask = text_mask(layer.size, x, y, text, font)
    stroke_mask = Image.new("L", layer.size, 0)
    ImageDraw.Draw(stroke_mask).text(
        (x, y), text, font=font, fill=255,
        stroke_width=stroke_width, stroke_fill=255,
    )
    outer_mask = Image.new("L", layer.size, 0)
    ImageDraw.Draw(outer_mask).text(
        (x, y), text, font=font, fill=255,
        stroke_width=stroke_width + 4, stroke_fill=255,
    )

    apply_wordart_text(layer, fill_mask, stroke_mask, outer_mask, palette)
    add_text_pattern(layer, fill_mask, (x, y, w, h), palette)
    add_text_sheen(layer, fill_mask, (x, y, w, h), opacity=88)


def draw_featured_spaced_first_word(layer, x, y, text, font, palette,
                                    spacing, stroke_width=2, wave=0):
    d = ImageDraw.Draw(layer)
    w, h = spaced_text_width(d, text, font, spacing, stroke_width=stroke_width)

    draw_varied_spaced_text(
        d, x + 7, y + 7, text, font, fill=palette["shadow"],
        spacing=spacing, stroke_width=stroke_width,
        stroke_fill=palette["shadow"], wave=wave,
    )
    fill_mask = spaced_text_mask(layer.size, x, y, text, font, spacing, wave,
                                 stroke_width=0)
    stroke_mask = spaced_text_mask(layer.size, x, y, text, font, spacing, wave,
                                   stroke_width=stroke_width)
    outer_mask = spaced_text_mask(layer.size, x, y, text, font, spacing, wave,
                                  stroke_width=stroke_width + 3)

    apply_wordart_text(layer, fill_mask, stroke_mask, outer_mask, palette)
    add_text_pattern(layer, fill_mask, (x, y, w, h), palette)
    add_text_sheen(layer, fill_mask, (x, y, w, h), opacity=82)


def make_distressed_alpha(alpha, strength=0.18):
    noise = Image.effect_noise(alpha.size, 95).convert("L")
    cutoff = int(255 * (1 - strength))
    holes = noise.point(lambda p: 255 if p > cutoff else 0)
    return Image.composite(Image.new("L", alpha.size, 0), alpha, holes)


def apply_distress(layer, strength=0.16):
    alpha = layer.getchannel("A")
    new_alpha = make_distressed_alpha(alpha, strength)
    layer.putalpha(new_alpha)
    return layer


def draw_flourish(draw, cx, y, width, color, line_width=3):
    left = cx - width // 2
    right = cx + width // 2
    draw.line((left, y, right, y), fill=color, width=line_width)
    r = 10
    draw.arc((left - r * 2, y - r, left, y + r), 270, 90, fill=color, width=line_width)
    draw.arc((right, y - r, right + r * 2, y + r), 90, 270, fill=color, width=line_width)
    dot_r = 4
    draw.ellipse((cx - dot_r, y - dot_r, cx + dot_r, y + dot_r), fill=color)


# ---------------------------------------------------------------------------
# PREFIX / SUBTITLE RENDERING (NEW)
# ---------------------------------------------------------------------------
def _draw_centered_plain_text(img, text, font, y, canvas_w, palette,
                              stroke_width=1, tracking=0):
    """Draw text horizontally centered at y with a soft shadow + outline."""
    d = ImageDraw.Draw(img)
    bbox = d.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    tw = bbox[2] - bbox[0]

    if tracking > 0:
        # Manual tracking for a more "postcard caption" feel.
        total = 0
        char_boxes = []
        for ch in text:
            cb = d.textbbox((0, 0), ch, font=font, stroke_width=stroke_width)
            char_boxes.append((ch, cb[2] - cb[0]))
            total += cb[2] - cb[0] + tracking
        total -= tracking
        x = (canvas_w - total) // 2
        for ch, cw in char_boxes:
            d.text((x + 2, y + 2), ch, font=font,
                   fill=palette["shadow"], stroke_width=stroke_width,
                   stroke_fill=palette["shadow"])
            d.text((x, y), ch, font=font, fill=palette["main"],
                   stroke_width=stroke_width, stroke_fill=palette["outline"])
            x += cw + tracking
    else:
        x = (canvas_w - tw) // 2
        d.text((x + 2, y + 2), text, font=font,
               fill=palette["shadow"], stroke_width=stroke_width,
               stroke_fill=palette["shadow"])
        d.text((x, y), text, font=font, fill=palette["main"],
               stroke_width=stroke_width, stroke_fill=palette["outline"])


def _render_prefix_and_subtitle(img, wa_bbox, prefix, subtitle,
                                prefix_font_path, subtitle_font_path,
                                H, palette, tracking=6):
    """Render optional prefix above and subtitle below the word-art block."""
    d = ImageDraw.Draw(img)
    canvas_w = img.size[0]

    if prefix and prefix_font_path:
        prefix_text = prefix.upper()
        prefix_size = max(18, int(H * 0.11))
        prefix_font = ImageFont.truetype(prefix_font_path, prefix_size)
        pb = d.textbbox((0, 0), prefix_text, font=prefix_font)
        ph = pb[3] - pb[1]
        gap = max(10, int(H * 0.05))
        py = wa_bbox[1] - ph - gap
        _draw_centered_plain_text(
            img, prefix_text, prefix_font, py, canvas_w, palette,
            stroke_width=1, tracking=tracking,
        )

    if subtitle and subtitle_font_path:
        subtitle_size = max(18, int(H * 0.13))
        subtitle_font = ImageFont.truetype(subtitle_font_path, subtitle_size)
        sb = d.textbbox((0, 0), subtitle, font=subtitle_font)
        sh = sb[3] - sb[1]
        gap = max(10, int(H * 0.06))
        sy = wa_bbox[3] + gap
        _draw_centered_plain_text(
            img, subtitle, subtitle_font, sy, canvas_w, palette,
            stroke_width=1, tracking=max(2, tracking // 2),
        )


# ---------------------------------------------------------------------------
# MAIN ENTRY POINT
# ---------------------------------------------------------------------------
def postcard_place_text(
    place_name,
    output_path=None,
    canvas_size=(1200, 500),
    seed=None,
    style_override=None,
    color_mode=None,
    # --- Smart positioning ------------------------------------------------
    position="auto",              # "auto" | "top" | "center" | "bottom"
    background=None,              # PIL.Image, path str, or None
    composite_background=False,   # if True and background given, output includes bg
    adaptive_contrast=True,       # auto-tune palette against the bg
    # --- Bilingual / caption extras ---------------------------------------
    prefix=None,                  # e.g. "GREETINGS FROM"
    subtitle=None,                # e.g. "東京" or "TOKYO · JAPAN"
    subtitle_font_path=None,
    prefix_font_path=None,
):
    """
    Transparent postcard-style place-name artwork.

    Smart positioning:
        - If `background` is given and `position="auto"`, the calmest
          (least busy) band of the background is chosen automatically.
        - Text is always horizontally centered; vertical position depends
          on the chosen band.

    Adaptive contrast:
        - If `background` is given and `adaptive_contrast=True`, the
          palette fill/outline is nudged so the text stays readable.

    Optional caption chrome:
        - `prefix` (e.g. "GREETINGS FROM") renders above the word art.
        - `subtitle` (e.g. local script) renders below the word art.
    """

    if seed is not None:
        random.seed(seed)

    place_name = place_name.strip()
    if not place_name:
        raise ValueError("place_name cannot be empty")

    final_W, final_H = canvas_size
    W = max(64, int(final_W * TITLE_SCALE))
    H = max(64, int(final_H * TITLE_SCALE))
    PAD = int(max(W, H) * 0.24)  # a touch more room for prefix/subtitle
    render_size = (W + PAD * 2, H + PAD * 2)

    # ---- Load background -------------------------------------------------
    bg_img = None
    if background is not None:
        if isinstance(background, Image.Image):
            bg_img = background
        elif isinstance(background, str):
            bg_img = Image.open(background)
        if bg_img is not None and bg_img.mode != "RGB":
            bg_img = bg_img.convert("RGB")

    # ---- Decide vertical position ----------------------------------------
    if position == "auto":
        if bg_img is not None:
            position = pick_smart_position(bg_img, canvas_size)
        else:
            # No bg: default to the classic postcard caption position.
            position = random.choice(["bottom", "bottom", "top", "center"])

    # ---- Sample bg luminance for adaptive contrast -----------------------
    bg_lum = None
    if bg_img is not None and adaptive_contrast:
        bg_lum = sample_background_luminance(bg_img, canvas_size, position)

    # ---- Base canvases ---------------------------------------------------
    img = Image.new("RGBA", render_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # ---- Fonts -----------------------------------------------------------
    rounded_path = find_font(bold=True, mood="rounded")
    display_path = find_font(bold=True, mood="display")
    hand_path = find_font(bold=False, mood="hand")
    regular_path = rounded_path
    bold_path = random.choice([display_path, rounded_path])
    script_path = find_font(bold=False, mood="script")

    bubble_path = find_font_from_candidates([
        "garden/assets/fonts/BubblegumSans/BubblegumSans-Regular.ttf",
        "garden/assets/fonts/FredokaOne/FredokaOne-Regular.ttf",
        "garden/assets/fonts/Baloo2/Baloo2-Bold.ttf",
        display_path,
    ]) or display_path

    condensed_path = find_font_from_candidates([
        "garden/assets/fonts/Oswald/Oswald-Bold.ttf",
        "garden/assets/fonts/BebasNeue/BebasNeue-Regular.ttf",
        "garden/assets/fonts/Staatliches/Staatliches-Regular.ttf",
        "garden/assets/fonts/Anton/Anton-Regular.ttf",
        display_path,
    ]) or display_path

    marker_path = find_font_from_candidates([
        "garden/assets/fonts/PermanentMarker/PermanentMarker-Regular.ttf",
        "garden/assets/fonts/Caveat/Caveat-Bold.ttf",
        "garden/assets/fonts/ShadowsIntoLight/ShadowsIntoLight-Regular.ttf",
        hand_path,
    ]) or hand_path

    cursive_path = find_font_from_candidates([
        "garden/assets/fonts/GreatVibes/GreatVibes-Regular.ttf",
        "garden/assets/fonts/Pacifico/Pacifico-Regular.ttf",
        "garden/assets/fonts/DancingScript/DancingScript-Bold.ttf",
        script_path,
    ]) or script_path

    classic_path = find_font_from_candidates([
        "garden/assets/fonts/PlayfairDisplay/PlayfairDisplay-Bold.ttf",
        "garden/assets/fonts/Cinzel/Cinzel-Bold.ttf",
        "garden/assets/fonts/AbrilFatface/AbrilFatface-Regular.ttf",
        "garden/assets/fonts/ArchivoBlack/ArchivoBlack-Regular.ttf",
        display_path,
    ]) or display_path

    words = place_name.split()
    first_word = words[0].upper()
    rest_words = " ".join(words[1:]).upper()

    style_pool = [
        "big_first_small_rest",
        "wide_first_script_rest",
        "giant_block",
        "thin_art_deco",
        "shadow_poster",
        "signature_mix",
        "retro_condensed",
        "script_luxe",
        "pop_bubble",
    ]
    style = style_override if style_override in style_pool else random.choice(style_pool)

    style_mode_defaults = {
        "pop_bubble":      "candy",
        "retro_condensed": "chrome",
        "script_luxe":     "metallic_gold",
        "thin_art_deco":   "neon",
    }

    selected_mode = (
        color_mode
        if color_mode in {"smart", "chrome", "neon", "candy", "metallic_gold"}
        else style_mode_defaults.get(style, "smart")
    )
    palette = random.choice(build_wordart_palettes(
        selected_mode,
        place_name=place_name,
        style=style,
    ))

    # NEW: adapt palette to background luminance.
    if bg_lum is not None:
        palette = adapt_palette_to_background(palette, bg_lum)

    layer = Image.new("RGBA", render_size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    # ---------------------------------------------------------------------
    #  Style branches
    # ---------------------------------------------------------------------
    if style == "big_first_small_rest":
        first_font = fit_font(d, first_word, classic_path,
                              W * 0.9, H * 0.34, 160, stroke_width=3)
        bbox = d.textbbox((0, 0), first_word, font=first_font, stroke_width=3)
        fw = bbox[2] - bbox[0]
        x = (W - fw) // 2
        y = int(H * 0.14)
        draw_featured_first_word(layer, x, y, first_word, first_font, palette,
                                 stroke_width=3)
        if rest_words:
            word_bottom = featured_word_bottom(d, first_word, first_font,
                                               stroke_width=3, shadow_depth=14)
            rest_font = fit_font(d, rest_words, rounded_path,
                                 W * 0.72, H * 0.14, 48, stroke_width=1)
            spacing = random.randint(4, 10)
            rw, _ = spaced_text_width(d, rest_words, rest_font, spacing,
                                      stroke_width=1)
            sub_y = y + word_bottom + 24
            draw_spaced_text(d, (W - rw) // 2, sub_y, rest_words, rest_font,
                             fill=palette["accent"], spacing=spacing,
                             stroke_width=1, stroke_fill=palette["outline"])

    elif style == "wide_first_script_rest":
        first_font = fit_font(d, first_word, cursive_path,
                              W * 0.85, H * 0.26, 105, stroke_width=1)
        spacing = random.randint(8, 18)
        fw, _ = spaced_text_width(d, first_word, first_font, spacing, stroke_width=1)
        while fw > W * 0.88 and spacing > 2:
            spacing -= 2
            fw, _ = spaced_text_width(d, first_word, first_font, spacing, stroke_width=1)
        x = (W - fw) // 2
        y = int(H * 0.16)
        draw_featured_spaced_first_word(layer, x, y, first_word, first_font, palette,
                                        spacing=spacing, stroke_width=1, wave=3)
        if rest_words:
            word_bottom = featured_word_bottom(d, first_word, first_font,
                                               stroke_width=1, shadow_depth=7)
            rest_font = fit_font(d, rest_words, condensed_path,
                                 W * 0.74, H * 0.20, 68)
            bbox = d.textbbox((0, 0), rest_words, font=rest_font, stroke_width=2)
            rw = bbox[2] - bbox[0]
            d.text(((W - rw) // 2, y + word_bottom + 28), rest_words, font=rest_font,
                   fill=palette["accent"], stroke_width=2,
                   stroke_fill=palette["outline"])

    elif style == "giant_block":
        text = place_name.upper()
        font = fit_font(d, text, condensed_path, W * 0.9, H * 0.5, 145, stroke_width=4)
        bbox = d.textbbox((0, 0), text, font=font, stroke_width=4)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (W - tw) // 2
        y = (H - th) // 2
        for off in range(12, 2, -3):
            d.text((x + off, y + off), text, font=font,
                   fill=palette["shadow"], stroke_width=4,
                   stroke_fill=palette["shadow"])
        d.text((x + 5, y - 4), text, font=font, fill=palette["accent"],
               stroke_width=3, stroke_fill=palette["outline"])
        d.text((x, y), text, font=font, fill=palette["main"],
               stroke_width=4, stroke_fill=palette["outline"])
        mask = text_mask(render_size, x, y, text, font)
        add_text_pattern(layer, mask, (x, y, tw, th), palette)
        add_text_sheen(layer, mask, (x, y, tw, th), opacity=76)

    elif style == "thin_art_deco":
        text = place_name.upper()
        font = fit_font(d, text, marker_path, W * 0.85, H * 0.35, 100, stroke_width=1)
        spacing = random.randint(10, 18)
        tw, th = spaced_text_width(d, text, font, spacing, stroke_width=1)
        while tw > W * 0.9 and spacing > 2:
            spacing -= 2
            tw, th = spaced_text_width(d, text, font, spacing, stroke_width=1)
        x = (W - tw) // 2
        y = (H - th) // 2
        draw_varied_spaced_text(d, x, y, text, font, fill=palette["main"],
                                spacing=spacing, stroke_width=1,
                                stroke_fill=palette["outline"], wave=2)
        mask = spaced_text_mask(render_size, x, y, text, font, spacing, wave=2)
        add_text_pattern(layer, mask, (x, y, tw, th), palette)
        add_text_sheen(layer, mask, (x, y, tw, th), opacity=64)

    elif style == "shadow_poster":
        first_font = fit_font(d, first_word, classic_path,
                              W * 0.86, H * 0.34, 135, stroke_width=2)
        bbox = d.textbbox((0, 0), first_word, font=first_font, stroke_width=2)
        fw = bbox[2] - bbox[0]
        x = (W - fw) // 2
        y = int(H * 0.18)
        draw_featured_first_word(layer, x, y, first_word, first_font, palette,
                                 stroke_width=2)
        if rest_words:
            word_bottom = featured_word_bottom(d, first_word, first_font,
                                               stroke_width=2, shadow_depth=14)
            rest_font = fit_font(d, rest_words, bubble_path, W * 0.7, H * 0.18, 48)
            spacing = random.randint(4, 10)
            rw, _ = spaced_text_width(d, rest_words, rest_font, spacing)
            rx = (W - rw) // 2
            ry = y + word_bottom + 20
            draw_spaced_text(d, rx + 3, ry + 3, rest_words, rest_font,
                             fill=palette["shadow"], spacing=spacing,
                             stroke_width=1, stroke_fill=palette["shadow"])
            draw_spaced_text(d, rx, ry, rest_words, rest_font,
                             fill=palette["accent"], spacing=spacing,
                             stroke_width=1, stroke_fill=palette["outline"])

    elif style == "signature_mix":
        first_font = fit_font(d, first_word, classic_path,
                              W * 0.82, H * 0.28, 118, stroke_width=3)
        bbox = d.textbbox((0, 0), first_word, font=first_font, stroke_width=3)
        fw = bbox[2] - bbox[0]
        x = (W - fw) // 2
        y = int(H * 0.14)
        draw_featured_first_word(layer, x, y, first_word, first_font, palette,
                                 stroke_width=3)
        if rest_words:
            word_bottom = featured_word_bottom(d, first_word, first_font,
                                               stroke_width=3, shadow_depth=14)
            rest_font = fit_font(d, rest_words,
                                 random.choice([cursive_path, marker_path]),
                                 W * 0.78, H * 0.18, 66, stroke_width=1)
            spacing = random.randint(2, 6)
            rw, rh = spaced_text_width(d, rest_words, rest_font, spacing, stroke_width=1)
            rx = (W - rw) // 2
            ry = y + word_bottom + 12
            draw_varied_spaced_text(d, rx, ry, rest_words, rest_font,
                                    fill=palette["accent"], spacing=spacing,
                                    stroke_width=1, stroke_fill=palette["outline"],
                                    wave=2)
            mask = spaced_text_mask(render_size, rx, ry, rest_words, rest_font,
                                    spacing, wave=2)
            add_text_pattern(layer, mask, (rx, ry, rw, rh), palette)
            add_text_sheen(layer, mask, (rx, ry, rw, rh), opacity=56)

    elif style == "retro_condensed":
        text = place_name.upper()
        font = fit_font(d, text, condensed_path, W * 0.88, H * 0.38, 126, stroke_width=3)
        spacing = random.randint(5, 12)
        tw, th = spaced_text_width(d, text, font, spacing, stroke_width=2)
        while tw > W * 0.92 and spacing > 1:
            spacing -= 1
            tw, th = spaced_text_width(d, text, font, spacing, stroke_width=2)
        x = (W - tw) // 2
        y = int(H * 0.36)
        draw_spaced_text(d, x + 6, y + 8, text, font, fill=palette["shadow"],
                         spacing=spacing, stroke_width=2, stroke_fill=palette["shadow"])
        draw_spaced_text(d, x, y, text, font, fill=palette["main"],
                         spacing=spacing, stroke_width=2, stroke_fill=palette["outline"])
        mask = spaced_text_mask(render_size, x, y, text, font, spacing, wave=0)
        add_text_pattern(layer, mask, (x, y, tw, th), palette)
        add_text_sheen(layer, mask, (x, y, tw, th), opacity=62)

    elif style == "script_luxe":
        first_font = fit_font(d, first_word, cursive_path,
                              W * 0.78, H * 0.28, 122, stroke_width=2)
        bbox = d.textbbox((0, 0), first_word, font=first_font, stroke_width=2)
        fw = bbox[2] - bbox[0]
        x = (W - fw) // 2
        y = int(H * 0.14)
        draw_featured_first_word(layer, x, y, first_word, first_font, palette,
                                 stroke_width=2)
        if rest_words:
            word_bottom = featured_word_bottom(d, first_word, first_font,
                                               stroke_width=2, shadow_depth=14)
            rest_font = fit_font(d, rest_words, classic_path,
                                 W * 0.72, H * 0.20, 58, stroke_width=1)
            spacing = random.randint(6, 12)
            rw, rh = spaced_text_width(d, rest_words, rest_font, spacing, stroke_width=1)
            rx = (W - rw) // 2
            ry = y + word_bottom + 18
            draw_spaced_text(d, rx, ry, rest_words, rest_font,
                             fill=palette["accent"], spacing=spacing,
                             stroke_width=1, stroke_fill=palette["outline"])
            mask = spaced_text_mask(render_size, rx, ry, rest_words, rest_font, spacing, wave=0)
            add_text_sheen(layer, mask, (rx, ry, rw, rh), opacity=50)

    elif style == "pop_bubble":
        text = place_name.upper()
        font = fit_font(d, text, bubble_path, W * 0.84, H * 0.42, 132, stroke_width=3)
        bbox = d.textbbox((0, 0), text, font=font, stroke_width=3)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (W - tw) // 2
        y = int(H * 0.3)
        for off in (10, 6, 3):
            d.text((x + off, y + off), text, font=font, fill=palette["shadow"],
                   stroke_width=3, stroke_fill=palette["shadow"])
        d.text((x, y), text, font=font, fill=palette["main"],
               stroke_width=3, stroke_fill=palette["outline"])
        mask = text_mask(render_size, x, y, text, font)
        add_text_pattern(layer, mask, (x, y, tw, th), palette)
        add_text_sheen(layer, mask, (x, y, tw, th), opacity=66)

    img = Image.alpha_composite(img, layer)

    # ---- Optional prefix + subtitle --------------------------------------
    wa_bbox = img.getbbox()
    if wa_bbox and (prefix or subtitle):
        prefix_path = find_font_from_candidates([
            "garden/assets/fonts/Oswald/Oswald-Bold.ttf",
            "garden/assets/fonts/BebasNeue/BebasNeue-Regular.ttf",
            "garden/assets/fonts/Staatliches/Staatliches-Regular.ttf",
            "garden/assets/fonts/DMSans/DMSans[opsz,wght].ttf",
            display_path,
        ], randomize=False) or prefix_font_path or display_path

        sub_path = _pick_subtitle_font(subtitle_font_path, subtitle or place_name)

        _render_prefix_and_subtitle(
            img, wa_bbox,
            prefix=prefix,
            subtitle=subtitle,
            prefix_font_path=prefix_font_path or prefix_path,
            subtitle_font_path=sub_path,
            H=H,
            palette=palette,
        )

    # ---- Crop to visible content -----------------------------------------
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
    content_w, content_h = img.size

    # ---- Scale to fit final canvas ---------------------------------------
    MARGIN_X      = int(final_W * 0.04)
    MARGIN_TOP    = int(final_H * 0.05)
    MARGIN_BOTTOM = int(final_H * 0.05)

    max_w = final_W - 2 * MARGIN_X
    max_h = final_H - MARGIN_TOP - MARGIN_BOTTOM

    if content_w > max_w or content_h > max_h:
        scale = min(max_w / content_w, max_h / content_h)
        img = img.resize(
            (max(1, int(content_w * scale)), max(1, int(content_h * scale))),
            Image.Resampling.LANCZOS,
        )
        content_w, content_h = img.size

    # ---- Position based on `position` ------------------------------------
    paste_x = (final_W - content_w) // 2  # always horizontal center

    if position == "top":
        paste_y = MARGIN_TOP
    elif position == "bottom":
        paste_y = final_H - MARGIN_BOTTOM - content_h
    else:  # center
        band_h = final_H - MARGIN_TOP - MARGIN_BOTTOM
        paste_y = MARGIN_TOP + (band_h - content_h) // 2

    # Clamp so nothing leaves the canvas.
    paste_y = max(MARGIN_TOP, min(paste_y, final_H - MARGIN_BOTTOM - content_h))
    paste_x = max(MARGIN_X, min(paste_x, final_W - MARGIN_X - content_w))

    final_img = Image.new("RGBA", (final_W, final_H), (0, 0, 0, 0))
    final_img.paste(img, (paste_x, paste_y), img)

    # ---- Optionally composite onto the background ------------------------
    if composite_background and bg_img is not None:
        bg_resized = bg_img.resize((final_W, final_H), Image.Resampling.LANCZOS)
        if bg_resized.mode != "RGBA":
            bg_resized = bg_resized.convert("RGBA")
        bg_resized.alpha_composite(final_img)
        final_img = bg_resized

    if output_path:
        final_img.save(output_path)


    return final_img