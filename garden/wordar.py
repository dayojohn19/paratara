from PIL import Image, ImageDraw, ImageFont, ImageFilter
import random
import math


def art(
    text,
    output_path="postcard_word_art.png",
    size=(1600, 1000),
    font_path=None,
    accent_text=None,
):
    """
    Generate advanced postcard-style word art.

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

    # ---------- Background gradient ----------
    img = Image.new("RGB", size)
    pixels = img.load()

    top_color = (255, 190, 130)
    bottom_color = (90, 150, 220)

    for y in range(height):
        ratio = y / height
        r = int(top_color[0] * (1 - ratio) + bottom_color[0] * ratio)
        g = int(top_color[1] * (1 - ratio) + bottom_color[1] * ratio)
        b = int(top_color[2] * (1 - ratio) + bottom_color[2] * ratio)
        for x in range(width):
            pixels[x, y] = (r, g, b)

    draw = ImageDraw.Draw(img)

    # ---------- Sun / postcard decorative shapes ----------
    for radius in range(260, 0, -8):
        alpha_ratio = radius / 260
        color = (
            int(255 * alpha_ratio + 255 * (1 - alpha_ratio)),
            int(220 * alpha_ratio + 160 * (1 - alpha_ratio)),
            int(100 * alpha_ratio + 80 * (1 - alpha_ratio)),
        )
        bbox = (
            width // 2 - radius,
            height // 2 - radius,
            width // 2 + radius,
            height // 2 + radius,
        )
        draw.ellipse(bbox, fill=color)

    # ---------- Decorative rays ----------
    ray_layer = Image.new("RGBA", size, (0, 0, 0, 0))
    ray_draw = ImageDraw.Draw(ray_layer)

    center = (width // 2, height // 2)
    for i in range(24):
        angle1 = math.radians(i * 15)
        angle2 = math.radians(i * 15 + 7)

        p1 = center
        p2 = (
            center[0] + int(math.cos(angle1) * width),
            center[1] + int(math.sin(angle1) * width),
        )
        p3 = (
            center[0] + int(math.cos(angle2) * width),
            center[1] + int(math.sin(angle2) * width),
        )

        ray_draw.polygon([p1, p2, p3], fill=(255, 255, 255, 28))

    img = Image.alpha_composite(img.convert("RGBA"), ray_layer)

    # ---------- Fonts ----------
    if font_path:
        main_font = ImageFont.truetype(font_path, 170)
        accent_font = ImageFont.truetype(font_path, 58)
    else:
        # Default fallback font
        main_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 170)
        accent_font = ImageFont.truetype("DejaVuSans.ttf", 58)

    # ---------- Main text position ----------
    draw = ImageDraw.Draw(img)
    bbox = draw.textbbox((0, 0), text, font=main_font, stroke_width=8)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    x = (width - text_w) // 2
    y = (height - text_h) // 2 - 30

    # ---------- Text shadow ----------
    shadow_layer = Image.new("RGBA", size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow_layer)

    shadow_draw.text(
        (x + 16, y + 18),
        text,
        font=main_font,
        fill=(0, 0, 0, 180),
        stroke_width=10,
        stroke_fill=(0, 0, 0, 180),
    )

    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(8))
    img = Image.alpha_composite(img, shadow_layer)

    # ---------- Text glow ----------
    glow_layer = Image.new("RGBA", size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)

    glow_draw.text(
        (x, y),
        text,
        font=main_font,
        fill=(255, 255, 255, 170),
        stroke_width=16,
        stroke_fill=(255, 255, 255, 120),
    )

    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(12))
    img = Image.alpha_composite(img, glow_layer)

    # ---------- Main text with stroke ----------
    text_layer = Image.new("RGBA", size, (0, 0, 0, 0))
    text_draw = ImageDraw.Draw(text_layer)

    text_draw.text(
        (x, y),
        text,
        font=main_font,
        fill=(255, 245, 180),
        stroke_width=8,
        stroke_fill=(95, 40, 120),
    )

    img = Image.alpha_composite(img, text_layer)

    # ---------- Highlight line on text ----------
    highlight_layer = Image.new("RGBA", size, (0, 0, 0, 0))
    highlight_draw = ImageDraw.Draw(highlight_layer)

    highlight_draw.text(
        (x - 3, y - 8),
        text,
        font=main_font,
        fill=(255, 255, 255, 75),
        stroke_width=1,
        stroke_fill=(255, 255, 255, 70),
    )

    img = Image.alpha_composite(img, highlight_layer)

    # ---------- Accent text ----------
    if accent_text:
        accent_layer = Image.new("RGBA", size, (0, 0, 0, 0))
        accent_draw = ImageDraw.Draw(accent_layer)

        accent_bbox = accent_draw.textbbox((0, 0), accent_text, font=accent_font)
        accent_w = accent_bbox[2] - accent_bbox[0]

        accent_draw.text(
            ((width - accent_w) // 2, y + text_h + 70),
            accent_text,
            font=accent_font,
            fill=(255, 255, 255, 230),
            stroke_width=3,
            stroke_fill=(60, 70, 120, 210),
        )

        img = Image.alpha_composite(img, accent_layer)

    # ---------- Decorative dots/stars ----------
    decor_layer = Image.new("RGBA", size, (0, 0, 0, 0))
    decor_draw = ImageDraw.Draw(decor_layer)

    for _ in range(180):
        px = random.randint(40, width - 40)
        py = random.randint(40, height - 40)
        radius = random.choice([1, 2, 3])
        alpha = random.randint(60, 170)

        decor_draw.ellipse(
            (px - radius, py - radius, px + radius, py + radius),
            fill=(255, 255, 255, alpha),
        )

    img = Image.alpha_composite(img, decor_layer)

    # ---------- Paper texture ----------
    texture = Image.new("RGBA", size, (0, 0, 0, 0))
    texture_pixels = texture.load()

    for y_pos in range(height):
        for x_pos in range(width):
            noise = random.randint(0, 28)
            texture_pixels[x_pos, y_pos] = (noise, noise, noise, 24)

    img = Image.alpha_composite(img, texture)

    # ---------- Postcard border ----------
    final_draw = ImageDraw.Draw(img)

    border_margin = 35
    final_draw.rounded_rectangle(
        (
            border_margin,
            border_margin,
            width - border_margin,
            height - border_margin,
        ),
        radius=35,
        outline=(255, 255, 255, 220),
        width=8,
    )

    final_draw.rounded_rectangle(
        (
            border_margin + 18,
            border_margin + 18,
            width - border_margin - 18,
            height - border_margin - 18,
        ),
        radius=26,
        outline=(90, 60, 120, 160),
        width=3,
    )

    # ---------- Save ----------
    img = img.convert("RGB")
    img.save(output_path, quality=95)

    return output_path