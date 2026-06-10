

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


def spaced_text_mask(size, x, y, text, font, spacing=10, wave=0):
    mask = Image.new("L", size, 0)
    d = ImageDraw.Draw(mask)

    for i, char in enumerate(text):
        offset_y = int(wave * (1 if i % 2 == 0 else -1))
        d.text((x, y + offset_y), char, font=font, fill=255)
        bbox = d.textbbox((0, 0), char, font=font)
        x += bbox[2] - bbox[0] + spacing + (i % 3)

    return mask


def add_clipped_letter_details(layer, mask, accent, outline):
    pattern = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    p = ImageDraw.Draw(pattern)
    W, H = layer.size

    for y in range(18, H, 38):
        p.line((-80, y + 26, W + 80, y - 26), fill=accent[:3] + (95,), width=5)

    for x in range(35, W, 86):
        for y in range(28, H, 92):
            r = 3
            p.ellipse((x - r, y - r, x + r, y + r), fill=outline[:3] + (80,))

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

    d.text(
        (x, y),
        text,
        font=font,
        fill=palette["main"],
        stroke_width=stroke_width,
        stroke_fill=palette["outline"],
    )

    mask = text_mask(layer.size, x, y, text, font)
    add_clipped_letter_details(layer, mask, palette["accent"], palette["outline"])
    draw_first_name_ornaments(d, x, y, w, h, palette)


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
    draw_varied_spaced_text(
        d,
        x,
        y,
        text,
        font,
        fill=palette["main"],
        spacing=spacing,
        stroke_width=stroke_width,
        stroke_fill=palette["outline"],
        wave=wave,
    )

    mask = spaced_text_mask(layer.size, x, y, text, font, spacing, wave)
    add_clipped_letter_details(layer, mask, palette["accent"], palette["outline"])
    draw_first_name_ornaments(d, x, y, w, h, palette)


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

    regular_path = find_font(bold=False, mood=random.choice(["hand", "script"]))
    bold_path = find_font(bold=True, mood=random.choice(["display", "rounded"]))
    script_path = find_font(bold=False, mood="script")

    words = place_name.split()
    first_word = words[0].upper()
    rest_words = " ".join(words[1:]).upper()

    palette = random.choice([
        {
            "main": (246, 229, 181, 255),
            "outline": (55, 45, 40, 255),
            "shadow": (80, 55, 45, 160),
            "accent": (197, 130, 61, 255),
        },
        {
            "main": (42, 112, 120, 255),
            "outline": (245, 235, 200, 255),
            "shadow": (32, 54, 68, 150),
            "accent": (230, 176, 89, 255),
        },
        {
            "main": (248, 245, 225, 255),
            "outline": (40, 75, 82, 255),
            "shadow": (25, 42, 58, 170),
            "accent": (219, 96, 78, 255),
        },
        {
            "main": (62, 54, 66, 255),
            "outline": (244, 224, 206, 255),
            "shadow": (120, 80, 70, 150),
            "accent": (216, 122, 104, 255),
        },
        {
            "main": (255, 238, 180, 255),
            "outline": (38, 82, 94, 255),
            "shadow": (18, 44, 56, 165),
            "accent": (239, 109, 82, 255),
        },
        {
            "main": (246, 244, 222, 255),
            "outline": (104, 50, 63, 255),
            "shadow": (65, 38, 51, 150),
            "accent": (77, 153, 141, 255),
        },
        {
            "main": (235, 202, 113, 255),
            "outline": (41, 44, 70, 255),
            "shadow": (28, 30, 52, 165),
            "accent": (226, 91, 91, 255),
        },
        {
            "main": (112, 174, 166, 255),
            "outline": (255, 244, 210, 255),
            "shadow": (26, 69, 75, 155),
            "accent": (245, 184, 96, 255),
        },
        {
            "main": (255, 249, 232, 255),
            "outline": (79, 91, 63, 255),
            "shadow": (48, 62, 48, 155),
            "accent": (202, 94, 73, 255),
        },
        {
            "main": (219, 91, 76, 255),
            "outline": (252, 237, 200, 255),
            "shadow": (112, 53, 54, 150),
            "accent": (54, 135, 137, 255),
        },
    ])

    style = random.choice([
        "big_first_small_rest",
        "wide_first_script_rest",
        "stacked_label",
        "giant_block",
        "thin_art_deco",
        "shadow_poster",
    ])

    layer = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    if style == "big_first_small_rest":
        first_font = fit_font(
            d,
            first_word,
            bold_path,
            W * 0.9,
            H * 0.45,
            160,
            stroke_width=3,
        )

        bbox = d.textbbox((0, 0), first_word, font=first_font, stroke_width=3)
        fw = bbox[2] - bbox[0]
        fh = bbox[3] - bbox[1]

        x = (W - fw) // 2
        y = int(H * 0.18)

        draw_featured_first_word(layer, x, y, first_word, first_font, palette, stroke_width=3)

        if rest_words:
            rest_font = fit_font(
                d,
                rest_words,
                regular_path,
                W * 0.72,
                H * 0.16,
                48,
                stroke_width=1,
            )

            spacing = random.randint(8, 20)
            rw, rh = spaced_text_width(d, rest_words, rest_font, spacing, stroke_width=1)

            rx = (W - rw) // 2
            ry = y + fh + 25

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

            draw_flourish(
                d,
                W // 2,
                ry + rh + 30,
                min(420, rw),
                palette["accent"],
                line_width=3,
            )

    elif style == "wide_first_script_rest":
        first_font = fit_font(
            d,
            first_word,
            script_path,
            W * 0.85,
            H * 0.32,
            105,
            stroke_width=1,
        )

        spacing = random.randint(12, 28)
        fw, fh = spaced_text_width(d, first_word, first_font, spacing, stroke_width=1)

        while fw > W * 0.88 and spacing > 2:
            spacing -= 2
            fw, fh = spaced_text_width(d, first_word, first_font, spacing, stroke_width=1)

        x = (W - fw) // 2
        y = int(H * 0.18)

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
            rest_font = fit_font(d, rest_words, bold_path, W * 0.7, H * 0.25, 70)
            bbox = d.textbbox((0, 0), rest_words, font=rest_font, stroke_width=2)
            rw = bbox[2] - bbox[0]
            rh = bbox[3] - bbox[1]

            rx = (W - rw) // 2
            ry = y + fh + 35

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
            bold_path,
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
        add_clipped_letter_details(layer, text_mask(canvas_size, x, y, text, font), palette["accent"], palette["outline"])

        draw_flourish(d, W // 2, y + th + 35, min(500, tw), palette["accent"], 4)

    elif style == "thin_art_deco":
        text = place_name.upper()
        font = fit_font(
            d,
            text,
            regular_path,
            W * 0.85,
            H * 0.35,
            100,
            stroke_width=1,
        )

        spacing = random.randint(14, 30)
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
        add_clipped_letter_details(layer, spaced_text_mask(canvas_size, x, y, text, font, spacing, wave=2), palette["accent"], palette["outline"])

        top_y = y - 28
        bottom_y = y + th + 28

        d.line((x, top_y, x + tw, top_y), fill=palette["accent"], width=3)
        d.line((x, bottom_y, x + tw, bottom_y), fill=palette["accent"], width=3)

    elif style == "shadow_poster":
        first_font = fit_font(
            d,
            first_word,
            bold_path,
            W * 0.86,
            H * 0.44,
            135,
            stroke_width=2,
        )

        bbox = d.textbbox((0, 0), first_word, font=first_font, stroke_width=2)
        fw = bbox[2] - bbox[0]
        fh = bbox[3] - bbox[1]

        x = (W - fw) // 2
        y = int(H * 0.2)

        draw_featured_first_word(layer, x, y, first_word, first_font, palette, stroke_width=2)

        if rest_words:
            rest_font = fit_font(d, rest_words, regular_path, W * 0.65, H * 0.16, 42)
            spacing = random.randint(10, 22)
            rw, rh = spaced_text_width(d, rest_words, rest_font, spacing)

            rx = (W - rw) // 2
            ry = y + fh + 18

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
                wave=1,
            )

    # Random distress sometimes
    if random.random() < 0.45:
        layer = apply_distress(layer, strength=random.uniform(0.08, 0.2))

    # Slight blur and sharpen-ish overlay for vintage print softness
    if random.random() < 0.25:
        soft = layer.filter(ImageFilter.GaussianBlur(0.35))
        layer = Image.alpha_composite(layer, soft)

    img = Image.alpha_composite(img, layer)

    if output_path:
        img.save(output_path)

    return img
