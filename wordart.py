from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os, random
from PIL import ImageOps
import requests, io
import os, io, requests
from PIL import ImageFont

def gradient_text(draw, text, font, position, size, colors,direction="horizontal"):
    text_w, text_h = size

    # --- Create smooth gradient using PIL ---
    gradient_img = Image.new("L", (text_w, text_h))
    pixels = gradient_img.load()
    
    if direction == "horizontal":
        for y in range(text_h):
            for x in range(text_w):
                pixels[x, y] = int((x / (text_w - 1)) * 255) if text_w > 1 else 0
    else:  # vertical
        for y in range(text_h):
            val = int((y / (text_h - 1)) * 255) if text_h > 1 else 0
            for x in range(text_w):
                pixels[x, y] = val

    # Colorize the grayscale gradient → RGB gradient
    colored_gradient = ImageOps.colorize(gradient_img, colors[0], colors[1])

    # Create text mask (white text on black)
    mask = Image.new("L", (text_w, text_h), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.text((0, 0), text, font=font, fill=255)

    return colored_gradient, mask
def get_random_font(font_dir="garden/assets/fonts", font_size=90):
    # List all .ttf and .otf files in the folder
    fonts = [f for f in os.listdir(font_dir) if f.lower().endswith((".ttf", ".otf"))]
    if not fonts:
        raise Exception("❌ No .ttf or .otf fonts found in the folder.")
    
    # Pick one random font
    font_file = random.choice(fonts)
    font_path = os.path.join(font_dir, font_file)

    print(f"🎨 Using font: {font_file}")
    return ImageFont.truetype(font_path, font_size)

def create_wordart(text: str, width=1500, height=350,text_outline_color = (0,0,0,255)):
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = get_random_font()

    # Center text
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    text_x = (width - text_w) // 2
    # text_y = (height - text_h) // 2
    text_y = 35

    # for blur_radius, color in [(15, (255, 0, 255, 90)), (8, (0, 255, 255, 100))]:
    #     glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    #     gdraw = ImageDraw.Draw(glow)
    #     gdraw.text((text_x, text_y), text, font=font, fill=color)
    #     glow = glow.filter(ImageFilter.GaussianBlur(blur_radius))
    #     img = Image.alpha_composite(img, glow)

    # --- Outline ---
    outline = Image.new("RGBA", img.size, (0, 0, 0, 0))
    odraw = ImageDraw.Draw(outline)
    # for dx in range(-2, 3):
    #     for dy in range(-2, 3):
    #         odraw.text((text_x + dx, text_y + dy), text, font=font, fill=(text_outline_color))
    fill = tuple(random.randint(0, 255) for _ in range(3)) + (255,)
    for dx in range(-3, 4):
        for dy in range(-3, 4):
            odraw.text((text_x + dx, text_y + dy), text, font=font, fill=fill)            
    img = Image.alpha_composite(img, outline)

    # --- Main text ---
    draw = ImageDraw.Draw(img)
    # white text background
    fill = tuple(random.randint(0, 255) for _ in range(3)) + (255,)
    draw.text((text_x, text_y), text, font=font, fill=fill)

    # Slight blur for smooth glow edges
    # img = img.filter(ImageFilter.GaussianBlur(0.4))
    

    # shine = Image.new("RGBA", img.size, (0, 0, 0, 0))
    # shine_draw = ImageDraw.Draw(shine)
    # shine_draw.text((text_x, text_y - 5), text, font=font, fill=(255, 255, 255, 60))
    # shine = shine.filter(ImageFilter.GaussianBlur(6))
    # img = Image.alpha_composite(img, shine)

    depth = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(depth)
    for offset in range(10):  # depth layers
        d.text((text_x + offset, text_y + offset), text, font=font, fill=(20, 20, 20, 80))
    img = Image.alpha_composite(depth, img)


    gradient, mask = gradient_text(draw, text, font, (text_x, text_y), (text_w, text_h), ("#00FFFF", "#FF00FF"))
    img.paste(gradient, (text_x, text_y), mask)

    return img
header_img = create_wordart("Test1 Texta  asd asd")
header_img.save("garden/generated_header.png", format="PNG")