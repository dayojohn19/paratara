

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
import random
import os


def find_font(bold=False, mood=None):
    font_sets = {
        "display": [
            "garden/assets/fonts/Knewave-Regular.ttf",
            "garden/assets/fonts/BubblegumSans-Regular.ttf",
            "garden/assets/fonts/AutourOne-Regular.ttf",
            "garden/assets/fonts/Kranky-Regular.ttf",
            "garden/assets/fonts/Sunshiney-Regular.ttf",
            "garden/assets/fonts/mickey-mouse-font/MickeyMousePersonalUseRegular-mLRAG.otf",
            "garden/assets/fonts/ve-gg-y-font/VeggyPersonalUseSemiExpandedMedium-1GMov.ttf",
            "garden/assets/fonts/daisys-font/DaisyspersonaluseBold-eZOBB.otf",
            "garden/assets/fonts/helvetica-255/Helvetica-Bold.ttf",
            "garden/assets/fonts/dejavu-sans/DejaVuSans-BoldOblique.ttf",
            "garden/assets/fonts/dejavu-sans/DejaVuSansCondensed-Bold.ttf",
        ],
        "script": [
            "garden/assets/fonts/Great_Vibes/GreatVibes-Regular.ttf",
            "garden/assets/fonts/LeckerliOne-Regular.ttf",
            "garden/assets/fonts/daisy-script-font/DaisyscriptpersonaluseBold-p723D.otf",
            "garden/assets/fonts/daisys-font/DaisyspersonaluseBold-eZOBB.otf",
            "garden/assets/fonts/Caveat-VariableFont_wght.ttf",
            "garden/assets/fonts/CedarvilleCursive-Regular.ttf",
            "garden/assets/fonts/NanumPenScript-Regular.ttf",
            "garden/assets/fonts/EastSeaDokdo-Regular.ttf",
            "garden/assets/fonts/dejavu-sans/DejaVuSans-Oblique.ttf",
            "garden/assets/fonts/dejavu-sans/DejaVuSansCondensed-Oblique.ttf",
        ],
        "hand": [
            "garden/assets/fonts/PermanentMarker-Regular.ttf",
            "garden/assets/fonts/GochiHand-Regular.ttf",
            "garden/assets/fonts/ShadowsIntoLight-Regular.ttf",
            "garden/assets/fonts/RockSalt-Regular.ttf",
            "garden/assets/fonts/Kranky-Regular.ttf",
            "garden/assets/fonts/Sunshiney-Regular.ttf",
            "garden/assets/fonts/EastSeaDokdo-Regular.ttf",
            "garden/assets/fonts/NanumPenScript-Regular.ttf",
            "garden/assets/fonts/dejavu-sans/DejaVuSans-Oblique.ttf",
            "garden/assets/fonts/dejavu-sans/DejaVuSansCondensed-Oblique.ttf",
        ],
        "rounded": [
            "garden/assets/fonts/helvetica-255/helvetica-rounded-bold-5871d05ead8de.otf",
            "garden/assets/fonts/BubblegumSans-Regular.ttf",
            "garden/assets/fonts/dmsans/DMSans[opsz,wght].ttf",
            "garden/assets/fonts/inter/Inter[slnt,wght].ttf",
            "garden/assets/fonts/dejavu-sans/DejaVuSansCondensed-Bold.ttf",
            "garden/assets/fonts/dejavu-sans/DejaVuSansCondensed.ttf",
        ],
    }

    candidates = []
    if mood:
        candidates += font_sets.get(mood, [])

    if bold:
        candidates += font_sets["display"] + font_sets["rounded"]
    else:
        candidates += font_sets["hand"] + font_sets["script"]

    candidates += [
        "garden/assets/fonts/helvetica-255/Helvetica-Bold.ttf",
        "garden/assets/fonts/helvetica-255/helvetica-rounded-bold-5871d05ead8de.otf",
        "garden/assets/fonts/dmsans/DMSans[opsz,wght].ttf",
        "garden/assets/fonts/inter/Inter[slnt,wght].ttf",
        "garden/assets/fonts/dejavu-sans/DejaVuSans-Bold.ttf",
        "garden/assets/fonts/dejavu-sans/DejaVuSans.ttf",
        "garden/assets/fonts/dejavu-sans/DejaVuSansCondensed.ttf",
        "home/static/home/ttf/Montserrat/static/dejavu-sans/DejaVuSans-Bold.ttf",
        "home/static/home/ttf/Montserrat/static/dejavu-sans/DejaVuSans.ttf",
        "home/static/home/ttf/Montserrat/static/dejavu-sans/DejaVuSansCondensed.ttf",
    ]

    for path in candidates:
        if os.path.exists(path):
            return path

    raise RuntimeError("No font found. Add your own .ttf font path.")


def find_font_from_candidates(candidates):
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def text_bbox(draw, text, font, stroke_width=0):
    return draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)


def fit_font(draw, text, font_path, max_width, max_height, start_size, min_size=18, stroke_width=0):
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


def clamp_rgb(rgb):
    return tuple(max(0, min(255, int(v))) for v in rgb)


def mix_rgb(rgb_a, rgb_b, ratio):
    return clamp_rgb(
        (
            rgb_a[0] * (1.0 - ratio) + rgb_b[0] * ratio,
            rgb_a[1] * (1.0 - ratio) + rgb_b[1] * ratio,
            rgb_a[2] * (1.0 - ratio) + rgb_b[2] * ratio,
        )
    )


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


def build_wordart_palettes(mode="smart"):
    smart_pairs = [
        ((18, 30, 44), (248, 251, 255)),
        ((242, 247, 255), (22, 34, 49)),
        ((26, 73, 108), (245, 248, 252)),
        ((110, 28, 38), (252, 241, 228)),
        ((27, 79, 53), (248, 244, 232)),
    ]

    mode_map = {
        "smart": [make_wordart_palette(fill_rgb, outline_rgb) for fill_rgb, outline_rgb in smart_pairs],
        "chrome": [
            make_wordart_palette((224, 232, 244), (34, 46, 66), (116, 140, 178)),
            make_wordart_palette((242, 245, 250), (28, 36, 52), (152, 166, 188)),
            make_wordart_palette((210, 220, 236), (20, 30, 46), (100, 120, 152)),
        ],
        "neon": [
            make_wordart_palette((76, 255, 235), (12, 35, 50), (7, 214, 255)),
            make_wordart_palette((255, 94, 214), (48, 10, 44), (255, 170, 70)),
            make_wordart_palette((178, 255, 82), (22, 46, 20), (69, 230, 160)),
        ],
        "candy": [
            make_wordart_palette((255, 189, 210), (86, 41, 58), (255, 126, 170)),
            make_wordart_palette((255, 216, 166), (95, 56, 32), (255, 149, 95)),
            make_wordart_palette((194, 232, 255), (44, 70, 96), (129, 178, 255)),
        ],
        "metallic_gold": [
            make_wordart_palette((245, 214, 120), (66, 45, 14), (222, 170, 58)),
            make_wordart_palette((255, 226, 142), (74, 52, 18), (228, 183, 80)),
            make_wordart_palette((232, 191, 98), (58, 39, 12), (209, 150, 52)),
        ],
    }

    return mode_map.get(mode, mode_map["smart"])


def spaced_text_width(draw, text, font, spacing=10, stroke_width=0):
    total = 0
    max_h = 0

    for char in text:
        bbox = draw.textbbox((0, 0), char, font=font, stroke_width=stroke_width)
        total += bbox[2] - bbox[0] + spacing
        max_h = max(max_h, bbox[3] - bbox[1])

    return max(0, total - spacing), max_h


def draw_spaced_text(
    draw,
    x,
    y,
    text,
    font,
    fill,
    spacing=10,
    stroke_width=0,
    stroke_fill=None
):
    for char in text:
        draw.text(
            (x, y),
            char,
            font=font,
            fill=fill,
            stroke_width=stroke_width,
            stroke_fill=stroke_fill,
        )

        bbox = draw.textbbox((0, 0), char, font=font, stroke_width=stroke_width)
        x += bbox[2] - bbox[0] + spacing


def draw_varied_spaced_text(
    draw,
    x,
    y,
    text,
    font,
    fill,
    spacing=10,
    stroke_width=0,
    stroke_fill=None,
    wave=0,
):
    for i, char in enumerate(text):
        offset_y = int(wave * (1 if i % 2 == 0 else -1))
        draw.text(
            (x, y + offset_y),
            char,
            font=font,
            fill=fill,
            stroke_width=stroke_width,
            stroke_fill=stroke_fill,
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
        d.text((x, y + offset_y), char, font=font, fill=255, stroke_width=stroke_width, stroke_fill=255)
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
    depth = Image.new("RGBA", layer.size, mix_rgb(palette["shadow"][:3], (0, 0, 0), 0.2) + (118,))
    depth.putalpha(ImageChops.multiply(depth.getchannel("A"), depth_alpha))
    depth = depth.filter(ImageFilter.GaussianBlur(1.2))
    layer.alpha_composite(depth)

    # Outer glow/rim gives text that classic word-art silhouette.
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

    # Add glossy top pass clipped to letters for a more modern word-art finish.
    w, h = layer.size
    gloss_col = Image.new("RGBA", (1, h), (255, 255, 255, 0))
    for y_pos in range(h):
        ratio = y_pos / max(h - 1, 1)
        if ratio <= 0.36:
            alpha = int((0.36 - ratio) / 0.36 * 122)
        else:
            alpha = 0
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
        draw.ellipse((cx - 8, top - 8, cx + 8, top + 8), outline=palette["accent"], width=3)
        draw_diamond(draw, cx, bottom, 9, palette["accent"])

    mid_y = y + h // 2
    for cx in (left, right):
        draw.arc((cx - 20, mid_y - 22, cx + 20, mid_y + 22), 80, 280, fill=palette["outline"], width=3)


def draw_featured_first_word(layer, x, y, text, font, palette, stroke_width=3):
    d = ImageDraw.Draw(layer)
    bbox = d.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]

    for off in (14, 9, 5):
        d.text(
            (x + off, y + off),
            text,
            font=font,
            fill=palette["shadow"],
            stroke_width=stroke_width,
            stroke_fill=palette["shadow"],
        )

    d.text(
        (x + 5, y - 4),
        text,
        font=font,
        fill=palette["accent"],
        stroke_width=max(1, stroke_width - 1),
        stroke_fill=palette["outline"],
    )

    fill_mask = text_mask(layer.size, x, y, text, font)
    stroke_mask = Image.new("L", layer.size, 0)
    ImageDraw.Draw(stroke_mask).text(
        (x, y),
        text,
        font=font,
        fill=255,
        stroke_width=stroke_width,
        stroke_fill=255,
    )
    outer_mask = Image.new("L", layer.size, 0)
    ImageDraw.Draw(outer_mask).text(
        (x, y),
        text,
        font=font,
        fill=255,
        stroke_width=stroke_width + 4,
        stroke_fill=255,
    )

    apply_wordart_text(layer, fill_mask, stroke_mask, outer_mask, palette)
    add_text_pattern(layer, fill_mask, (x, y, w, h), palette)
    add_text_sheen(layer, fill_mask, (x, y, w, h), opacity=88)


def draw_featured_spaced_first_word(layer, x, y, text, font, palette, spacing, stroke_width=2, wave=0):
    d = ImageDraw.Draw(layer)
    w, h = spaced_text_width(d, text, font, spacing, stroke_width=stroke_width)

    draw_varied_spaced_text(
        d,
        x + 7,
        y + 7,
        text,
        font,
        fill=palette["shadow"],
        spacing=spacing,
        stroke_width=stroke_width,
        stroke_fill=palette["shadow"],
        wave=wave,
    )
    fill_mask = spaced_text_mask(layer.size, x, y, text, font, spacing, wave, stroke_width=0)
    stroke_mask = spaced_text_mask(layer.size, x, y, text, font, spacing, wave, stroke_width=stroke_width)
    outer_mask = spaced_text_mask(layer.size, x, y, text, font, spacing, wave, stroke_width=stroke_width + 3)

    apply_wordart_text(layer, fill_mask, stroke_mask, outer_mask, palette)
    add_text_pattern(layer, fill_mask, (x, y, w, h), palette)
    add_text_sheen(layer, fill_mask, (x, y, w, h), opacity=82)


def make_distressed_alpha(alpha, strength=0.18):
    """
    Randomly removes tiny areas from text alpha to make it look old/postcard-like.
    """
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
    """
    Simple vintage decorative underline.
    """
    left = cx - width // 2
    right = cx + width // 2

    draw.line((left, y, right, y), fill=color, width=line_width)

    r = 10
    draw.arc((left - r * 2, y - r, left, y + r), 270, 90, fill=color, width=line_width)
    draw.arc((right, y - r, right + r * 2, y + r), 90, 270, fill=color, width=line_width)

    dot_r = 4
    draw.ellipse((cx - dot_r, y - dot_r, cx + dot_r, y + dot_r), fill=color)


def postcard_place_text(
    place_name,
    output_path=None,
    canvas_size=(1200, 500),
    seed=None,
    style_override=None,
    color_mode=None,
):
    """
    Transparent postcard-style place-name text.

    Features:
    - transparent background
    - random postcard typography
    - different design for first word
    - optional second-line subtitle word
    - outlines, shadows, distress, flourishes
    - randomized letter spacing
    """

    if seed is not None:
        random.seed(seed)

    place_name = place_name.strip()
    if not place_name:
        raise ValueError("place_name cannot be empty")

    W, H = canvas_size

    img = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    rounded_path = find_font(bold=True, mood="rounded")
    display_path = find_font(bold=True, mood="display")
    hand_path = find_font(bold=False, mood="hand")
    regular_path = rounded_path
    bold_path = random.choice([display_path, rounded_path])
    script_path = find_font(bold=False, mood="script")

    bubble_path = find_font_from_candidates([
        "garden/assets/fonts/BubblegumSans-Regular.ttf",
        "garden/assets/fonts/Knewave-Regular.ttf",
        display_path,
    ]) or display_path
    condensed_path = find_font_from_candidates([
        "garden/assets/fonts/dejavu-sans/DejaVuSansCondensed-Bold.ttf",
        "garden/assets/fonts/helvetica-255/Helvetica-Bold.ttf",
        rounded_path,
    ]) or rounded_path
    marker_path = find_font_from_candidates([
        "garden/assets/fonts/PermanentMarker-Regular.ttf",
        "garden/assets/fonts/GochiHand-Regular.ttf",
        hand_path,
    ]) or hand_path
    cursive_path = find_font_from_candidates([
        "garden/assets/fonts/Great_Vibes/GreatVibes-Regular.ttf",
        "garden/assets/fonts/Caveat-VariableFont_wght.ttf",
        script_path,
    ]) or script_path
    classic_path = find_font_from_candidates([
        "garden/assets/fonts/helvetica-255/Helvetica-Bold.ttf",
        "garden/assets/fonts/dejavu-sans/DejaVuSans-Bold.ttf",
        condensed_path,
    ]) or condensed_path

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

    # Style-specific default finish gives each style a more iconic word-art look.
    style_mode_defaults = {
        "pop_bubble": "candy",
        "retro_condensed": "chrome",
        "script_luxe": "metallic_gold",
        "thin_art_deco": "neon",
    }

    selected_mode = color_mode if color_mode in {"smart", "chrome", "neon", "candy", "metallic_gold"} else style_mode_defaults.get(style, "smart")
    palette = random.choice(build_wordart_palettes(selected_mode))

    layer = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    if style == "big_first_small_rest":
        first_font = fit_font(
            d,
            first_word,
            classic_path,
            W * 0.9,
            H * 0.45,
            160,
            stroke_width=3,
        )

        bbox = d.textbbox((0, 0), first_word, font=first_font, stroke_width=3)
        fw = bbox[2] - bbox[0]
        fh = bbox[3] - bbox[1]

        x = (W - fw) // 2
        y = int(H * 0.28)

        draw_featured_first_word(layer, x, y, first_word, first_font, palette, stroke_width=3)

        if rest_words:
            rest_font = fit_font(
                d,
                rest_words,
                rounded_path,
                W * 0.72,
                H * 0.16,
                48,
                stroke_width=1,
            )

            spacing = random.randint(4, 10)
            rw, rh = spaced_text_width(d, rest_words, rest_font, spacing, stroke_width=1)

            rx = (W - rw) // 2
            ry = y + fh + 22

            draw_spaced_text(
                d,
                rx,
                ry,
                rest_words,
                rest_font,
                fill=palette["accent"],
                spacing=spacing,
                stroke_width=1,
                stroke_fill=palette["outline"],
            )

    elif style == "wide_first_script_rest":
        first_font = fit_font(
            d,
            first_word,
            cursive_path,
            W * 0.85,
            H * 0.32,
            105,
            stroke_width=1,
        )

        spacing = random.randint(8, 18)
        fw, fh = spaced_text_width(d, first_word, first_font, spacing, stroke_width=1)

        while fw > W * 0.88 and spacing > 2:
            spacing -= 2
            fw, fh = spaced_text_width(d, first_word, first_font, spacing, stroke_width=1)

        x = (W - fw) // 2
        y = int(H * 0.28)

        draw_featured_spaced_first_word(
            layer,
            x,
            y,
            first_word,
            first_font,
            palette,
            spacing=spacing,
            stroke_width=1,
            wave=3,
        )

        if rest_words:
            rest_font = fit_font(d, rest_words, condensed_path, W * 0.74, H * 0.22, 68)
            bbox = d.textbbox((0, 0), rest_words, font=rest_font, stroke_width=2)
            rw = bbox[2] - bbox[0]
            rh = bbox[3] - bbox[1]

            rx = (W - rw) // 2
            ry = y + fh + 28

            d.text(
                (rx, ry),
                rest_words,
                font=rest_font,
                fill=palette["accent"],
                stroke_width=2,
                stroke_fill=palette["outline"],
            )

    elif style == "stacked_label":
        label_w = int(W * random.uniform(0.65, 0.88))
        label_h = int(H * random.uniform(0.38, 0.5))
        lx = (W - label_w) // 2
        ly = (H - label_h) // 2

        d.rounded_rectangle((lx, ly, lx + label_w, ly + label_h), radius=18, outline=palette["outline"], width=4)
        d.rounded_rectangle((lx + 15, ly + 15, lx + label_w - 15, ly + label_h - 15), radius=12, outline=palette["accent"], width=2)
        for line_y in (ly + 30, ly + label_h - 30):
            d.line((lx + 46, line_y, lx + label_w - 46, line_y), fill=palette["accent"], width=2)
            draw_diamond(d, lx + 28, line_y, 8, palette["accent"])
            draw_diamond(d, lx + label_w - 28, line_y, 8, palette["accent"])

        first_font = fit_font(
            d,
            first_word,
            bold_path,
            label_w * 0.82,
            label_h * 0.45,
            105,
            stroke_width=1,
        )

        bbox = d.textbbox((0, 0), first_word, font=first_font, stroke_width=1)
        fw = bbox[2] - bbox[0]
        fh = bbox[3] - bbox[1]

        fx = lx + (label_w - fw) // 2
        fy = ly + 38

        draw_featured_first_word(layer, fx, fy, first_word, first_font, palette, stroke_width=1)

        if rest_words:
            rest_font = fit_font(d, rest_words, regular_path, label_w * 0.72, label_h * 0.22, 45)
            spacing = random.randint(6, 14)
            rw, rh = spaced_text_width(d, rest_words, rest_font, spacing)

            rx = lx + (label_w - rw) // 2
            ry = fy + fh + 18

            draw_spaced_text(
                d,
                rx,
                ry,
                rest_words,
                rest_font,
                fill=palette["outline"],
                spacing=spacing,
            )

        layer = apply_distress(layer, strength=0.12)

    elif style == "giant_block":
        text = place_name.upper()
        font = fit_font(
            d,
            text,
            condensed_path,
            W * 0.9,
            H * 0.5,
            145,
            stroke_width=4,
        )

        bbox = d.textbbox((0, 0), text, font=font, stroke_width=4)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]

        x = (W - tw) // 2
        y = (H - th) // 2

        for off in range(12, 2, -3):
            d.text(
                (x + off, y + off),
                text,
                font=font,
                fill=palette["shadow"],
                stroke_width=4,
                stroke_fill=palette["shadow"],
            )

        d.text((x + 5, y - 4), text, font=font, fill=palette["accent"], stroke_width=3, stroke_fill=palette["outline"])
        d.text((x, y), text, font=font, fill=palette["main"], stroke_width=4, stroke_fill=palette["outline"])
        add_text_pattern(layer, text_mask(canvas_size, x, y, text, font), (x, y, tw, th), palette)
        add_text_sheen(layer, text_mask(canvas_size, x, y, text, font), (x, y, tw, th), opacity=76)

    elif style == "thin_art_deco":
        text = place_name.upper()
        font = fit_font(
            d,
            text,
            marker_path,
            W * 0.85,
            H * 0.35,
            100,
            stroke_width=1,
        )

        spacing = random.randint(10, 18)
        tw, th = spaced_text_width(d, text, font, spacing, stroke_width=1)

        while tw > W * 0.9 and spacing > 2:
            spacing -= 2
            tw, th = spaced_text_width(d, text, font, spacing, stroke_width=1)

        x = (W - tw) // 2
        y = (H - th) // 2

        draw_varied_spaced_text(
            d,
            x,
            y,
            text,
            font,
            fill=palette["main"],
            spacing=spacing,
            stroke_width=1,
            stroke_fill=palette["outline"],
            wave=2,
        )
        add_text_pattern(
            layer,
            spaced_text_mask(canvas_size, x, y, text, font, spacing, wave=2),
            (x, y, tw, th),
            palette,
        )
        add_text_sheen(
            layer,
            spaced_text_mask(canvas_size, x, y, text, font, spacing, wave=2),
            (x, y, tw, th),
            opacity=64,
        )

    elif style == "shadow_poster":
        first_font = fit_font(
            d,
            first_word,
            classic_path,
            W * 0.86,
            H * 0.44,
            135,
            stroke_width=2,
        )

        bbox = d.textbbox((0, 0), first_word, font=first_font, stroke_width=2)
        fw = bbox[2] - bbox[0]
        fh = bbox[3] - bbox[1]

        x = (W - fw) // 2
        y = int(H * 0.3)

        draw_featured_first_word(layer, x, y, first_word, first_font, palette, stroke_width=2)

        if rest_words:
            rest_font = fit_font(d, rest_words, bubble_path, W * 0.7, H * 0.18, 48)
            spacing = random.randint(4, 10)
            rw, rh = spaced_text_width(d, rest_words, rest_font, spacing)

            rx = (W - rw) // 2
            ry = y + fh + 20

            draw_spaced_text(
                d,
                rx + 3,
                ry + 3,
                rest_words,
                rest_font,
                fill=palette["shadow"],
                spacing=spacing,
                stroke_width=1,
                stroke_fill=palette["shadow"],
            )
            draw_spaced_text(
                d,
                rx,
                ry,
                rest_words,
                rest_font,
                fill=palette["accent"],
                spacing=spacing,
                stroke_width=1,
                stroke_fill=palette["outline"],
            )

    elif style == "signature_mix":
        first_font = fit_font(
            d,
            first_word,
            classic_path,
            W * 0.82,
            H * 0.32,
            118,
            stroke_width=3,
        )

        bbox = d.textbbox((0, 0), first_word, font=first_font, stroke_width=3)
        fw = bbox[2] - bbox[0]
        fh = bbox[3] - bbox[1]

        x = (W - fw) // 2
        y = int(H * 0.22)

        draw_featured_first_word(layer, x, y, first_word, first_font, palette, stroke_width=3)

        if rest_words:
            rest_font = fit_font(
                d,
                rest_words,
                random.choice([cursive_path, marker_path]),
                W * 0.78,
                H * 0.18,
                66,
                stroke_width=1,
            )
            spacing = random.randint(2, 6)
            rw, rh = spaced_text_width(d, rest_words, rest_font, spacing, stroke_width=1)
            rx = (W - rw) // 2
            ry = y + fh + 10

            draw_varied_spaced_text(
                d,
                rx,
                ry,
                rest_words,
                rest_font,
                fill=palette["accent"],
                spacing=spacing,
                stroke_width=1,
                stroke_fill=palette["outline"],
                wave=2,
            )
            rest_mask = spaced_text_mask(canvas_size, rx, ry, rest_words, rest_font, spacing, wave=2)
            add_text_pattern(layer, rest_mask, (rx, ry, rw, rh), palette)
            add_text_sheen(layer, rest_mask, (rx, ry, rw, rh), opacity=56)

    elif style == "retro_condensed":
        text = place_name.upper()
        font = fit_font(
            d,
            text,
            condensed_path,
            W * 0.88,
            H * 0.38,
            126,
            stroke_width=3,
        )

        spacing = random.randint(5, 12)
        tw, th = spaced_text_width(d, text, font, spacing, stroke_width=2)
        while tw > W * 0.92 and spacing > 1:
            spacing -= 1
            tw, th = spaced_text_width(d, text, font, spacing, stroke_width=2)

        x = (W - tw) // 2
        y = int(H * 0.36)

        draw_spaced_text(
            d,
            x + 6,
            y + 8,
            text,
            font,
            fill=palette["shadow"],
            spacing=spacing,
            stroke_width=2,
            stroke_fill=palette["shadow"],
        )
        draw_spaced_text(
            d,
            x,
            y,
            text,
            font,
            fill=palette["main"],
            spacing=spacing,
            stroke_width=2,
            stroke_fill=palette["outline"],
        )
        text_alpha = spaced_text_mask(canvas_size, x, y, text, font, spacing, wave=0)
        add_text_pattern(layer, text_alpha, (x, y, tw, th), palette)
        add_text_sheen(layer, text_alpha, (x, y, tw, th), opacity=62)

    elif style == "script_luxe":
        first_font = fit_font(
            d,
            first_word,
            cursive_path,
            W * 0.78,
            H * 0.34,
            122,
            stroke_width=2,
        )

        bbox = d.textbbox((0, 0), first_word, font=first_font, stroke_width=2)
        fw = bbox[2] - bbox[0]
        fh = bbox[3] - bbox[1]
        x = (W - fw) // 2
        y = int(H * 0.22)

        draw_featured_first_word(layer, x, y, first_word, first_font, palette, stroke_width=2)

        if rest_words:
            rest_font = fit_font(d, rest_words, classic_path, W * 0.72, H * 0.2, 58, stroke_width=1)
            spacing = random.randint(6, 12)
            rw, rh = spaced_text_width(d, rest_words, rest_font, spacing, stroke_width=1)
            rx = (W - rw) // 2
            ry = y + fh + 16

            draw_spaced_text(
                d,
                rx,
                ry,
                rest_words,
                rest_font,
                fill=palette["accent"],
                spacing=spacing,
                stroke_width=1,
                stroke_fill=palette["outline"],
            )
            rest_alpha = spaced_text_mask(canvas_size, rx, ry, rest_words, rest_font, spacing, wave=0)
            add_text_sheen(layer, rest_alpha, (rx, ry, rw, rh), opacity=50)

    elif style == "pop_bubble":
        text = place_name.upper()
        font = fit_font(
            d,
            text,
            bubble_path,
            W * 0.84,
            H * 0.42,
            132,
            stroke_width=3,
        )

        bbox = d.textbbox((0, 0), text, font=font, stroke_width=3)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        x = (W - tw) // 2
        y = int(H * 0.3)

        for off in (10, 6, 3):
            d.text(
                (x + off, y + off),
                text,
                font=font,
                fill=palette["shadow"],
                stroke_width=3,
                stroke_fill=palette["shadow"],
            )

        d.text((x, y), text, font=font, fill=palette["main"], stroke_width=3, stroke_fill=palette["outline"])
        text_alpha = text_mask(canvas_size, x, y, text, font)
        add_text_pattern(layer, text_alpha, (x, y, tw, th), palette)
        add_text_sheen(layer, text_alpha, (x, y, tw, th), opacity=66)

    img = Image.alpha_composite(img, layer)

    if output_path:
        img.save(output_path)

    return img
