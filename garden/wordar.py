from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageFilter


def _load_font(font_path, size, fallback_name):
    if font_path:
        return ImageFont.truetype(font_path, size)

    try:
        return ImageFont.truetype(fallback_name, size)
    except OSError:
        return ImageFont.load_default()


def art(
    text,
    output_path="postcard_word_art.png",
    size=(1600, 1000),
    font_path=None,
    accent_text=None,
):
    """
    Generate clean postcard-style word art focused on the main text.

    Requirements:
        pip install pillow

    Parameters:
        text: Main word art text
        output_path: File path for saved image
        size: Canvas size, e.g. (1600, 1000)
        font_path: Optional path to a .ttf font file
        accent_text: Optional smaller decorative text
    """

    width, height = size

    img = Image.new("RGBA", size, (0, 0, 0, 255))
    pixels = img.load()

    top_color = (255, 242, 227)
    bottom_color = (63, 112, 140)

    for y_pos in range(height):
        ratio = y_pos / max(height - 1, 1)
        r = int(top_color[0] * (1 - ratio) + bottom_color[0] * ratio)
        g = int(top_color[1] * (1 - ratio) + bottom_color[1] * ratio)
        b = int(top_color[2] * (1 - ratio) + bottom_color[2] * ratio)
        for x_pos in range(width):
            pixels[x_pos, y_pos] = (r, g, b, 255)

    backdrop = Image.new("RGBA", size, (0, 0, 0, 0))
    backdrop_draw = ImageDraw.Draw(backdrop)
    backdrop_draw.ellipse(
        (width * 0.18, height * 0.12, width * 0.82, height * 0.82),
        fill=(255, 222, 182, 135),
    )
    backdrop_draw.rounded_rectangle(
        (width * 0.08, height * 0.2, width * 0.92, height * 0.8),
        radius=int(height * 0.08),
        outline=(255, 255, 255, 32),
        width=2,
    )
    backdrop = backdrop.filter(ImageFilter.GaussianBlur(24))
    img = Image.alpha_composite(img, backdrop)

    vignette = Image.new("RGBA", size, (0, 0, 0, 0))
    vignette_draw = ImageDraw.Draw(vignette)
    vignette_draw.rounded_rectangle(
        (18, 18, width - 18, height - 18),
        radius=38,
        outline=(255, 255, 255, 120),
        width=3,
    )
    vignette_draw.rounded_rectangle(
        (0, 0, width - 1, height - 1),
        radius=44,
        outline=(18, 44, 58, 110),
        width=34,
    )
    vignette = vignette.filter(ImageFilter.GaussianBlur(2))
    img = Image.alpha_composite(img, vignette)

    main_font_size = min(int(height * 0.22), int(width / max(len(text), 1) * 2.15))
    main_font_size = max(main_font_size, 84)
    accent_font_size = max(int(main_font_size * 0.32), 26)

    main_font = _load_font(font_path, main_font_size, "DejaVuSans-Bold.ttf")
    accent_font = _load_font(font_path, accent_font_size, "DejaVuSans.ttf")

    draw = ImageDraw.Draw(img)
    bbox = draw.textbbox((0, 0), text, font=main_font, stroke_width=6)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    if text_w > width * 0.82:
        adjusted_size = max(int(main_font_size * (width * 0.82 / text_w)), 72)
        main_font = _load_font(font_path, adjusted_size, "DejaVuSans-Bold.ttf")
        accent_font = _load_font(font_path, max(int(adjusted_size * 0.32), 26), "DejaVuSans.ttf")
        bbox = draw.textbbox((0, 0), text, font=main_font, stroke_width=6)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

    x = (width - text_w) // 2
    y = (height - text_h) // 2 - (accent_font_size // 3 if accent_text else 0)

    glow_layer = Image.new("RGBA", size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)
    glow_draw.rounded_rectangle(
        (x - 80, y - 60, x + text_w + 80, y + text_h + 70),
        radius=46,
        fill=(255, 248, 240, 42),
    )
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(28))
    img = Image.alpha_composite(img, glow_layer)

    shadow_layer = Image.new("RGBA", size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow_layer)
    shadow_draw.text(
        (x + 10, y + 14),
        text,
        font=main_font,
        fill=(16, 36, 48, 180),
        stroke_width=8,
        stroke_fill=(16, 36, 48, 170),
    )
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(10))
    img = Image.alpha_composite(img, shadow_layer)

    text_mask = Image.new("L", size, 0)
    mask_draw = ImageDraw.Draw(text_mask)
    mask_draw.text((x, y), text, font=main_font, fill=255)

    text_fill = Image.new("RGBA", size, (0, 0, 0, 0))
    fill_pixels = text_fill.load()
    fill_top = (255, 245, 225)
    fill_bottom = (245, 168, 104)
    for y_pos in range(height):
        ratio = y_pos / max(height - 1, 1)
        r = int(fill_top[0] * (1 - ratio) + fill_bottom[0] * ratio)
        g = int(fill_top[1] * (1 - ratio) + fill_bottom[1] * ratio)
        b = int(fill_top[2] * (1 - ratio) + fill_bottom[2] * ratio)
        for x_pos in range(width):
            fill_pixels[x_pos, y_pos] = (r, g, b, 255)
    text_fill.putalpha(text_mask)
    img = Image.alpha_composite(img, text_fill)

    text_outline = Image.new("RGBA", size, (0, 0, 0, 0))
    outline_draw = ImageDraw.Draw(text_outline)
    outline_draw.text(
        (x, y),
        text,
        font=main_font,
        fill=(0, 0, 0, 0),
        stroke_width=6,
        stroke_fill=(38, 60, 76, 255),
    )
    img = Image.alpha_composite(img, text_outline)

    highlight_mask = Image.new("L", size, 0)
    highlight_draw = ImageDraw.Draw(highlight_mask)
    highlight_draw.text((x, y), text, font=main_font, fill=255)

    highlight = Image.new("RGBA", size, (0, 0, 0, 0))
    highlight_draw = ImageDraw.Draw(highlight)
    highlight_draw.rounded_rectangle(
        (x - 6, y - 2, x + text_w + 6, y + int(text_h * 0.34)),
        radius=20,
        fill=(255, 255, 255, 78),
    )
    highlight.putalpha(ImageChops.multiply(highlight.getchannel("A"), highlight_mask))
    highlight = highlight.filter(ImageFilter.GaussianBlur(4))
    img = Image.alpha_composite(img, highlight)

    if accent_text:
        accent_layer = Image.new("RGBA", size, (0, 0, 0, 0))
        accent_draw = ImageDraw.Draw(accent_layer)
        accent_bbox = accent_draw.textbbox((0, 0), accent_text, font=accent_font)
        accent_w = accent_bbox[2] - accent_bbox[0]
        accent_y = y + text_h + max(int(height * 0.04), 28)
        accent_draw.text(
            ((width - accent_w) // 2, accent_y),
            accent_text,
            font=accent_font,
            fill=(250, 251, 246, 240),
        )
        img = Image.alpha_composite(img, accent_layer)

    # ---------- Save ----------
    img = img.convert("RGB")
    img.save(output_path, quality=95)

    return output_path