import os
import os


def add_cut_rect_to_svg(svg_path, x, y, w, h, canvas_w_px, canvas_h_px):
    """
    Appends a cut rectangle to the SVG, centered within a 5mm safe margin.
    Matches a PIL layout that also uses a 5mm (60px) safe zone.
    """
    # 1. Standard A4 Dimensions in mm
    A4_W_MM, A4_H_MM = 210.0, 297.0
    
    # 2. Define Safe Margin (5mm)
    # This matches the shift you applied in your PIL paste logic
    MARGIN_MM = 5.0 
    
    # 3. Calculate usable space in mm
    usable_w_mm = A4_W_MM - (2 * MARGIN_MM)
    usable_h_mm = A4_H_MM - (2 * MARGIN_MM)

    # 4. Scaling
    # We scale based on the USABLE pixel area (e.g., 2360px) 
    # to the USABLE mm area (200mm)
    scale_x = usable_w_mm / canvas_w_px
    scale_y = usable_h_mm / canvas_h_px

    # 5. Coordinate Conversion
    # Position: Add the MARGIN_MM to shift the cut line away from the edge
    mm_x = round((x * scale_x) + MARGIN_MM, 2)
    mm_y = round((y * scale_y) + MARGIN_MM, 2)
    
    # Size: DO NOT add margin to width/height. 
    # The cutter should cut the exact size of the image.
    mm_w = round(w * scale_x, 2)
    mm_h = round(h * scale_y, 2)

    # 6. Generate SVG Tag
    new_rect = f'  <rect x="{mm_x}" y="{mm_y}" width="{mm_w}" height="{mm_h}" fill="none" stroke="red" stroke-width="0.5" />\n'

    if not os.path.exists(svg_path):
        with open(svg_path, 'w', encoding='utf-8') as f:
            f.write('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n')
            f.write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{A4_W_MM}mm" height="{A4_H_MM}mm" viewBox="0 0 {A4_W_MM} {A4_H_MM}">\n')
            # Optional: Draw a light gray rectangle to show the Safe Zone in your viewer
            f.write(f'  <rect x="{MARGIN_MM}" y="{MARGIN_MM}" width="{usable_w_mm}" height="{usable_h_mm}" fill="none" stroke="#eee" stroke-width="0.1" />\n')
            f.write(new_rect)
            f.write('</svg>')
    else:
        with open(svg_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        clean_lines = [l for l in lines if '</svg>' not in l]
        with open(svg_path, 'w', encoding='utf-8') as f:
            f.writelines(clean_lines)
            f.write(new_rect)
            f.write('</svg>')


def append_to_svg_cut_list(svg_path, boxes, canvas_w_px, canvas_h_px):
    """
    Creates an SVG with cut lines matching the PIL collage layout.
    :param svg_path: Path to save the .svg
    :param boxes: List of dicts [{'x':, 'y':, 'w':, 'h':}, ...] 
    :param canvas_w_px: Width of your A4 borders_collage in pixels
    :param canvas_h_px: Height of your A4 borders_collage in pixels
    """
    # A4 dimensions in mm
    A4_W_MM = 210
    A4_H_MM = 297
    # A4_WIDTH, A4_HEIGHT = 2480, 3508
    # Calculate scale factor (px to mm)
    scale_x = A4_W_MM / canvas_w_px
    scale_y = A4_H_MM / canvas_h_px

    svg_header = f'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg width="{A4_W_MM}mm" height="{A4_H_MM}mm" viewBox="0 0 {A4_W_MM} {A4_H_MM}" xmlns="http://www.w3.org/2000/svg">
    <!-- Main A4 Page Border -->
    <rect x="0" y="0" width="{A4_W_MM}" height="{A4_H_MM}" fill="none" stroke="black" stroke-width="0.1"/>
'''
    
    rects = ""
    for box in boxes:
        # Convert pixel coordinates to mm
        mm_x = box['x'] * scale_x
        mm_y = box['y'] * scale_y
        mm_w = box['w'] * scale_x
        mm_h = box['h'] * scale_y
        
        # Red stroke is standard for "Cut" lines
        rects += f'    <rect x="{mm_x}" y="{mm_y}" width="{mm_w}" height="{mm_h}" fill="none" stroke="red" stroke-width="0.2"/>\n'

    svg_footer = "</svg>"
    
    with open(svg_path, 'w') as f:
        print('Saving SVG cut list to:', svg_path)
        f.write(svg_header + rects + svg_footer)

def crop_center_square(img):
    """Crop the input PIL image to a centered square."""
    w, h = img.size
    min_side = min(w, h)
    left = (w - min_side) // 2
    top = (h - min_side) // 2
    right = left + min_side
    bottom = top + min_side
    return img.crop((left, top, right, bottom))
def fit_image_preserve_aspect(img, box_w, box_h):
    """Resize PIL image to fit within (box_w, box_h) preserving aspect ratio.
    Image is only scaled down (not enlarged) to avoid upscaling artifacts.
    Returns the resized image (may be original if it already fits).
    """
    orig_w, orig_h = img.size
    if orig_w == 0 or orig_h == 0 or box_w <= 0 or box_h <= 0:
        return img
    scale = min(box_w / orig_w, box_h / orig_h)
    if scale >= 1.0:
        return img
    new_w = max(1, int(orig_w * scale))
    new_h = max(1, int(orig_h * scale))
    return img.resize((new_w, new_h), Image.LANCZOS)
def find_matching_qr(master_path, qr_dir):
    """Find the best matching QR image for a given master image filename.
    Tries exact '-master' -> '-qr' replacement first, then searches for files
    containing the same unique code, and finally picks the closest name
    using a simple similarity heuristic.
    Returns full path or None if not found.
    """
    import re, difflib
    if not os.path.isdir(qr_dir):
        return None
    base = os.path.basename(master_path)
    stem = os.path.splitext(base)[0]
    exts = ['.png', '.jpg', '.jpeg']

    # 1) Exact replacement: replace '-master' with '-qr'
    if '-master' in stem:
        cand_stem = stem.replace('-master', '-qr')
        for ext in exts:
            candidate = os.path.join(qr_dir, cand_stem + ext)
            if os.path.exists(candidate):
                return candidate

    # 2) Try removing '-master' and looking for '*-qr' or files containing the unique code
    # Extract code (prefer uppercase alnum sequence used elsewhere)
    m = re.search(r'([A-Z0-9]{6,})', base)
    code = m.group(1) if m else None
    candidates = []
    if code:
        for f in os.listdir(qr_dir):
            if code.lower() in f.lower() and any(f.lower().endswith(e) for e in exts):
                candidates.append(os.path.join(qr_dir, f))
        # Prefer candidate that has '-qr' in its name
        if candidates:
            for c in candidates:
                if '-qr' in os.path.basename(c).lower():
                    return c
            # Else pick the most similar filename by simple ratio
            best = None
            best_ratio = 0.0
            for c in candidates:
                cand_stem = os.path.splitext(os.path.basename(c))[0]
                ratio = difflib.SequenceMatcher(None, stem.lower(), cand_stem.lower()).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best = c
            if best:
                return best

    # 3) Final fallback: look for same stem without '-master'
    base_no_master = stem.replace('-master', '')
    for ext in exts:
        candidate = os.path.join(qr_dir, base_no_master + ext)
        if os.path.exists(candidate):
            return candidate


    return None
from PIL import Image, ImageDraw
import math
import os
from datetime import datetime


def star_points(cx, cy, outer_radius, inner_radius, rotation_deg=90):
    points = []
    for index in range(10):
        radius = outer_radius if index % 2 == 0 else inner_radius
        angle = math.radians(rotation_deg + index * 36)
        x = cx + radius * math.cos(angle)
        y = cy + radius * math.sin(angle)
        points.append((x, y))
    return points


def build_three_star_emblem(size=28, outline="#F7D35B", stroke_width=2):
    canvas_w = int(size * 6.2)
    canvas_h = int(size * 6.0)
    emblem = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(emblem)

    gap = size * 1.35
    center_x = canvas_w * 0.36
    center_y = canvas_h * 0.5
    # Keep original spacing; only tilt each star so nearest tips face inward.
    star_specs = [
        (center_x, center_y - gap, 20),
        (center_x + gap * 1.45, center_y, 180),
        (center_x, center_y + gap, -20),
    ]

    for cx, cy, rot in star_specs:
        poly = star_points(cx, cy, size, size * 0.62, rotation_deg=rot)
        draw.polygon(poly, fill=(0, 0, 0, 0), outline=outline, width=stroke_width)

    return emblem.crop((0, 0, canvas_w, canvas_h))


def _draw_postcard_layout(borders_collage, x, y, w, h, rotate_90, place_logo_path=None, logo_path=None, border_px=4):
    # Paste QR code if posted_name is available
    posted_name = getattr(borders_collage, 'posted_name', None)
    if not isinstance(posted_name, str):
        posted_name = str(posted_name) if posted_name is not None else ""
    if posted_name:
        qr_dir = os.path.join(os.getcwd(), 'media', 'image_cards', 'qr')
        qr_basename = posted_name.replace('-master', '-qr')
        qr_path = os.path.join(qr_dir, qr_basename + '.png')
        filename = qr_path 
        itemgroupname = None
        if "group-" in filename:
            itemgroupname = filename.split("group-")[1].split(" place-")[0]
        itemplacename = None
        if "place-" in filename:
            itemplacename = filename.split("place-")[1].rsplit(".png", 1)[0]

        if not os.path.exists(qr_path):
            qr_path = os.path.join(qr_dir, qr_basename + '.jpg')
        if os.path.exists(qr_path):
            try:
                from PIL import Image as PILImage
                qr_img = PILImage.open(qr_path).convert("RGBA")
                base_qr_size = int(min(w, h) * 0.5)
                qr_size = int(base_qr_size * 1.20)
                padding = max(10, int(min(w, h) * 0.05))
                qr_size = min(qr_size, w - padding * 2, h - padding * 2)
                qr_img = qr_img.resize((qr_size, qr_size), PILImage.LANCZOS)
                qr_x = x + w - qr_size - padding
                qr_y = y + padding
                borders_collage.paste(qr_img, (qr_x, qr_y), qr_img)
                print(f"[Postcard] Pasted QR code from {qr_path} at ({qr_x},{qr_y}) size {qr_size}x{qr_size}")
            except Exception as e:
                print(f"[Postcard] Failed to paste QR code: {e}")
        else:
            print(f"[Postcard] No QR code found for {posted_name} at {qr_path}")
    else:
        print("[Postcard] No posted_name found for QR code lookup.")
    from PIL import Image as PILImage, ImageDraw as PILImageDraw, ImageFont
    # Draw border on the main borders_collage so it is always visible
    border_color = (0, 0, 0)  # Black border
    border_thickness = border_px
    # Set place_logo_path default to media/logo/diver_panglao.png using Django settings.MEDIA_ROOT or fallback

    print('Checking if place logo path is None')
    if place_logo_path is None:
        try:
            from django.conf import settings
            media_root = settings.MEDIA_ROOT
        except ImportError:
            media_root = os.path.join(os.getcwd(), 'media')
        place_logo_path = os.path.join(media_root, 'logo', 'diver_panglao.png')
    # Use the three-star emblem instead of the old paratara logo file.
    logo_path = None
    from PIL import Image as PILImage, ImageDraw as PILImageDraw, ImageFont

    postcard_img = PILImage.new('RGBA', (w, h), (255, 255, 255, 255))
    draw = PILImageDraw.Draw(postcard_img)

    def _srgb_channel_to_linear(channel):
        v = channel / 255.0
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4

    def _relative_luminance(rgb):
        r, g, b = rgb
        r_lin = _srgb_channel_to_linear(r)
        g_lin = _srgb_channel_to_linear(g)
        b_lin = _srgb_channel_to_linear(b)
        return (0.2126 * r_lin) + (0.7152 * g_lin) + (0.0722 * b_lin)

    def _contrast_ratio(rgb_a, rgb_b):
        l1 = _relative_luminance(rgb_a)
        l2 = _relative_luminance(rgb_b)
        lighter = max(l1, l2)
        darker = min(l1, l2)
        return (lighter + 0.05) / (darker + 0.05)

    def _clamp_rgb(rgb):
        return tuple(max(0, min(255, int(v))) for v in rgb)

    def _mix_rgb(rgb_a, rgb_b, ratio):
        return _clamp_rgb((
            rgb_a[0] * (1.0 - ratio) + rgb_b[0] * ratio,
            rgb_a[1] * (1.0 - ratio) + rgb_b[1] * ratio,
            rgb_a[2] * (1.0 - ratio) + rgb_b[2] * ratio,
        ))

    def _pick_title_palette(bg_rgb):
        fill_candidates = [
            (18, 30, 44),
            (242, 247, 255),
            (26, 73, 108),
            (110, 28, 38),
            (27, 79, 53),
        ]
        fill_color = max(fill_candidates, key=lambda c: _contrast_ratio(c, bg_rgb))

        outline_candidates = [
            (0, 0, 0),
            (255, 255, 255),
            _mix_rgb(fill_color, (0, 0, 0), 0.72),
            _mix_rgb(fill_color, (255, 255, 255), 0.72),
            _clamp_rgb((255 - bg_rgb[0], 255 - bg_rgb[1], 255 - bg_rgb[2])),
        ]

        def outline_score(outline):
            return min(_contrast_ratio(outline, fill_color), _contrast_ratio(outline, bg_rgb))

        outline_color = max(outline_candidates, key=outline_score)
        return fill_color, outline_color

    def _draw_title_with_style(base_img, text, font, fill_rgb, outline_rgb, style_name, y_top, rotate=False):
        title_bbox = font.getbbox(text)
        title_w = title_bbox[2] - title_bbox[0]
        title_h = title_bbox[3] - title_bbox[1]
        stroke_w = max(1, int(font.size * 0.08)) if hasattr(font, 'size') else 1
        pad = max(6, stroke_w * 3)

        layer_w = title_w + pad * 2
        layer_h = title_h + pad * 2
        text_layer = PILImage.new('RGBA', (layer_w, layer_h), (255, 255, 255, 0))
        text_draw = PILImageDraw.Draw(text_layer)

        if style_name == 'badge':
            bg_fill = _mix_rgb(fill_rgb, outline_rgb, 0.45)
            bg_alpha = 110
            radius = max(8, int(layer_h * 0.30))
            text_draw.rounded_rectangle((0, 0, layer_w - 1, layer_h - 1), radius=radius, fill=bg_fill + (bg_alpha,))
        elif style_name == 'underline':
            line_y = layer_h - max(3, int(layer_h * 0.12))
            text_draw.line([(pad, line_y), (layer_w - pad, line_y)], fill=outline_rgb + (180,), width=max(2, stroke_w))

        text_draw.text(
            (pad - title_bbox[0], pad - title_bbox[1]),
            text,
            fill=fill_rgb,
            font=font,
            stroke_width=stroke_w,
            stroke_fill=outline_rgb,
        )

        if rotate:
            text_layer = text_layer.rotate(90, expand=True)
            x_pos = (w - text_layer.width) // 2
            y_pos = y_top
            base_img.paste(text_layer, (x_pos, y_pos), text_layer)
        else:
            x_pos = int(w * 0.31) - (text_layer.width // 2)
            x_pos = max(0, min(w - text_layer.width, x_pos))
            base_img.paste(text_layer, (x_pos, y_top), text_layer)

    adaptive_title_text = ""
    adaptive_title_fill = (18, 30, 44)
    adaptive_title_stroke = (248, 251, 255)
    adaptive_title_bg = (245, 245, 245)

    # =========================
    # Title text
    # =========================
    font_path = os.path.join("garden", "assets", "fonts", "AutourOne-Regular.ttf")
    try:

        print("Font size:", int(h * 2))
        print("Font size:", int(h * 2))
        font_small = ImageFont.truetype(font_path, int(h * 0.015))
        bottom_font = ImageFont.truetype(font_path, int(h * 0.015))
        print("Font size:", int(h * 2))
    except:
        print('Error loadingfont_path using default font')
        font_big = font_small = ImageFont.load_default()


    # =========================
    # Diver image (RIGHT SIDE) will be pasted after drawing postcard text
    # (moved to bottom so the image is on top of other elements)
    # =========================

    # =========================
    # Logo (TOP LEFT)
    # =========================
    # paratara logo paste moved to after drawing postcard content so
    # it is placed on top together with the place logo.

    # =========================
    # Bottom layout (lines removed)
    # =========================
    # The vertical divider, message and address guide lines were removed
    # to avoid drawing thin or thick guideline lines on the postcard.

    # =========================
    # Rotation disabled: do not rotate postcard canvas by 90 degrees
    # =========================

    # Draw bottom-center site text (larger and more readable)

    # Paste the place_logo_path image on top with a small top padding
    # add here if vertical or horizontal
    print('Has place logo path:', place_logo_path)
    if place_logo_path:
        try:
            logo_img = PILImage.open(place_logo_path).convert("RGBA")

            # Use the upper area color as context for contrast-aware title styling.
            top_sample_h = max(1, int(logo_img.height * 0.35))
            sample_region = logo_img.crop((0, 0, logo_img.width, top_sample_h)).convert("RGB")
            sample_rgb = sample_region.resize((1, 1), PILImage.Resampling.BOX).getpixel((0, 0))
            adaptive_title_bg = sample_rgb
            adaptive_title_fill, adaptive_title_stroke = _pick_title_palette(adaptive_title_bg)

            # Keep a fixed published-by title; do not replace with place name text.

            logo_img = crop_center_square(logo_img)
            # Resize QR/logo to a larger target size and allow upscaling.
            target_size = int(min(w, h) * 0.35 * 1.20)
            if target_size < 1:
                target_size = min(w, h)
            if logo_img.width != target_size or logo_img.height != target_size:
                logo_img = logo_img.resize((target_size, target_size), PILImage.LANCZOS)
            right_padding = int(w * 0.06)
            top_padding = int(h * 0.04)
            print('Checking if rotate_90 :', rotate_90)
            if rotate_90:
                logo_img = logo_img.rotate(90, expand=True)
                paste_x = right_padding
                paste_y = top_padding
            else:
                paste_x = w - logo_img.width - right_padding
                paste_y = top_padding
                print("paste_x:", paste_x, "paste_y:", paste_y)
                print("image size:", w, h)
                print("logo size:", logo_img.size)

            postcard_img.paste(logo_img, (paste_x, paste_y), logo_img)
            os.remove(place_logo_path)
            print(f"[Collage] Deleted used qr image: {place_logo_path}")            
        except Exception as e:
            print(f"[Postcard] Failed to paste place logo on top: {e}")

    try:
        # Re-sample from the actual postcard title area to keep contrast reliable.
        title_band_h = max(24, int(h * 0.18))
        title_band_w = max(24, int(w * 0.60))
        title_band_x = max(0, int(w * 0.01))
        title_band = postcard_img.crop((title_band_x, 0, min(w, title_band_x + title_band_w), title_band_h)).convert("RGB")
        adaptive_title_bg = title_band.resize((1, 1), PILImage.Resampling.BOX).getpixel((0, 0))
        adaptive_title_fill, adaptive_title_stroke = _pick_title_palette(adaptive_title_bg)

        if adaptive_title_text.strip():
            title_font_size = max(18, int(h * 0.05))
            max_title_width = int(w * 0.58)
            while title_font_size >= 14:
                try:
                    title_font = ImageFont.truetype(font_path, title_font_size)
                except Exception:
                    title_font = ImageFont.load_default()
                title_bbox = title_font.getbbox(adaptive_title_text)
                title_w = title_bbox[2] - title_bbox[0]
                title_h = title_bbox[3] - title_bbox[1]
                if title_w <= max_title_width or title_font_size == 14:
                    break
                title_font_size -= 2

            title_top_padding = int(h * 0.05)
            title_len = len(adaptive_title_text.strip())
            if title_len <= 16:
                style_name = 'badge'
            elif title_len <= 30:
                style_name = 'underline'
            else:
                style_name = 'clean'

            _draw_title_with_style(
                postcard_img,
                adaptive_title_text,
                title_font,
                adaptive_title_fill,
                adaptive_title_stroke,
                style_name,
                title_top_padding,
                rotate=rotate_90,
            )
    except Exception as e:
        print(f"[Postcard] Failed to draw adaptive title: {e}")

    try:
        site_text = "Garden Home PostCard"
        footer_font_size = max(8, int(h * 0.018))
        try:
            footer_font = ImageFont.truetype(font_path, footer_font_size)
        except Exception:
            footer_font = ImageFont.load_default()

        footer_bbox = footer_font.getbbox(site_text)
        footer_w = footer_bbox[2] - footer_bbox[0]
        footer_h = footer_bbox[3] - footer_bbox[1]
        footer_padding = int(h * 0.03)

        if rotate_90:
            txt_layer = PILImage.new('RGBA', (footer_w, footer_h), (255, 255, 255, 0))
            txt_draw = PILImageDraw.Draw(txt_layer)
            txt_draw.text((-footer_bbox[0], -footer_bbox[1]), site_text, fill=(0, 0, 0), font=footer_font)
            rotated_txt = txt_layer.rotate(90, expand=True)
            text_x = w - rotated_txt.width - int(w * 0.05)
            text_y = h - rotated_txt.height - footer_padding
            postcard_img.paste(rotated_txt, (text_x, text_y), rotated_txt)
        else:
            text_x = (w - footer_w) // 2
            text_y = h - footer_h - footer_padding
            draw.text((text_x, text_y), site_text, fill=(0, 0, 0), font=footer_font)
    except Exception as e:
        print(f"[Postcard] Failed to draw footer text: {e}")


    if logo_path is None:
        try:
            emblem_size = max(6, int(min(w, h) * 0.02))
            star_logo = build_three_star_emblem(
                size=emblem_size,
                outline="#000000",
                stroke_width=max(1, emblem_size // 12),
            )
            # Move the emblem a bit lower and more inward while keeping it on-canvas.
            star_vertical_offset = int(h * 0.07)
            if rotate_90:
                star_logo = star_logo.rotate(90, expand=True)
                paste_x_left = int(w * 0.07)
                base_y = int(h - star_logo.height - int(h * 0.04))
                paste_y_same = min(h - star_logo.height, base_y + star_vertical_offset)
            else:
                paste_x_left = int(w * 0.07)
                paste_y_same = int(h * 0.04) + star_vertical_offset

            paste_x_left = max(0, min(w - star_logo.width, paste_x_left))
            paste_y_same = max(0, min(h - star_logo.height, paste_y_same))
            postcard_img.paste(star_logo, (paste_x_left, paste_y_same), star_logo)
        except Exception as e:
            print(f"[Postcard] Failed to paste three-star emblem on top: {e}")
    elif logo_path:
        try:
            par_logo = PILImage.open(logo_path).convert("RGBA")
            lw = int(w * 0.25)
            lh = int(h * 0.35)
            par_logo = fit_image_preserve_aspect(par_logo, lw, lh)
            if rotate_90:
                paste_x_left = int(w * 0.05) + max(0, (lw - par_logo.width) // 2)
                paste_y_same = int(h - h * 0.03 - par_logo.height)
                par_logo = par_logo.rotate(90, expand=True)
            else:
                paste_x_left = int(w * 0.05) + max(0, (lw - par_logo.width) // 2)
                paste_y_same = int(h * 0.03)

            postcard_img.paste(par_logo, (paste_x_left, paste_y_same), par_logo)
        except Exception as e:
            print(f"[Postcard] Failed to paste logo on top: {e}")

    
    # add here if vertical or horizontal
    # POST CARD CENTER LINES
    print('Drawing Lines')
    from PIL import ImageDraw
    
    w, h = postcard_img.size  # use SAME image
    print("Image size:", w, h)
    draw = ImageDraw.Draw(postcard_img)
    # ✔ correct vertical center (USE HEIGHT)
    center_y = h // 2
    center_x = w // 2

    canvas_w, canvas_h = borders_collage.size

        
    # # 1. Initialize a list to hold your cut coordinates
    # cut_boxes = []

    # # ... inside your loop where you define x, y, w, h for each postcard ...
    # # postcard_img = ... (your logic)
    # # borders_collage.paste(postcard_img, (x, y))

    # # 2. Save the coordinates for the SVG
    # cut_boxes.append({'x': center_x, 'y': center_y, 'w': w, 'h': h})

    # # 3. After the loop is finished and collage is saved:
    # canvas_w, canvas_h = borders_collage.size
    # svg_filename = "my_collage_cut_file.svg"

    # append_to_svg_cut_list(svg_filename, cut_boxes, canvas_w, canvas_h)    


    # Address guide lines area: approximately right 3/8 of postcard width.
    line_width = 2
    line_count = 5
    panel_ratio = 3.0 / 8.0
    dot_len = 7
    dot_gap = 6

    def draw_dotted_line(x1, y1, x2, y2, fill="black", width=2, dash_len=7, gap_len=6):
        if x1 == x2:
            # Vertical dotted line
            step = dash_len + gap_len
            start = min(y1, y2)
            end = max(y1, y2)
            y_pos = start
            while y_pos <= end:
                y_end = min(y_pos + dash_len - 1, end)
                draw.line([(x1, y_pos), (x2, y_end)], fill=fill, width=width)
                y_pos += step
        else:
            # Horizontal dotted line
            step = dash_len + gap_len
            start = min(x1, x2)
            end = max(x1, x2)
            x_pos = start
            while x_pos <= end:
                x_end = min(x_pos + dash_len - 1, end)
                draw.line([(x_pos, y1), (x_end, y2)], fill=fill, width=width)
                x_pos += step

    if rotate_90:
        print('Drawing Rotated Address Lines (compensated)')
        # Draw vertical lines in the top panel so downstream 90deg page rotation
        # lands as horizontal lines on the opposite side.
        panel_h = int(h * panel_ratio)
        panel_top = int(h * 0.04)
        panel_bottom = panel_top + panel_h
        side_padding = int(w * 0.08)

        first_x = int(w * 0.55)
        usable_w = int(w * 0.35)
        spacing = max(12, usable_w // max(1, line_count - 1))

        start_y = panel_top
        end_y = min(h - int(h * 0.04), panel_bottom)

        for i in range(line_count):
            xxx = min(w - side_padding, first_x + (i * spacing))
            draw_dotted_line(xxx, start_y, xxx, end_y, fill="black", width=line_width, dash_len=dot_len, gap_len=dot_gap)
    else:
        print('Drawing Address Lines on Right Side')
        panel_w = int(w * panel_ratio)
        panel_left = w - panel_w
        side_padding = int(panel_w * 0.12)

        start_x = panel_left + side_padding
        end_x = w - side_padding
        first_y = int(h * 0.38)
        usable_h = int(h * 0.42)
        spacing = max(12, usable_h // max(1, line_count - 1))

        for i in range(line_count):
            yyy = first_y + (i * spacing)
            draw_dotted_line(start_x, yyy, end_x, yyy, fill="black", width=line_width, dash_len=dot_len, gap_len=dot_gap)

    print("Line Draws")

    borders_collage.paste(postcard_img, (x, y), postcard_img)
    print(f"[Postcard] Drew styled postcard at ({x},{y}) size {w}x{h}")


def create_a4_collage_from_master_images(output_path=None, master_dir='image_cards/master', images_per_page=4, also_save_bordered=False, border_px=30, also_save_borders_only=True):

    """
    Loads up to 4 images from the master_dir, fits them into an A4-sized image, maximizing their height in each cell, rotating if needed, and saves the result. All images in a row will have the same height, and all in a column will have the same width, but images will not overlap. Used images are deleted from the master_dir. The output file is saved with a unique identifier.
    If also_save_bordered is True, also saves a bordered version with the same image sizes in a separate A4 collage.
    If also_save_borders_only is True, also saves a version with only the borders (empty boxes) at the same positions/sizes.
    """
    from PIL import ImageOps
    print('Going 1')
    import os
    try:
        from django.conf import settings
        media_root = settings.MEDIA_ROOT
    except ImportError:
        media_root = os.path.join(os.getcwd(), 'media')
    master_dir = os.path.join(media_root, 'image_cards', 'master')
    print('Going 2')
    print(f"[Collage] Starting collage creation. master_dir={master_dir}, images_per_page={images_per_page}, also_save_bordered={also_save_bordered}, border_px={border_px}, also_save_borders_only={also_save_borders_only}")
    # A4 size at 300 DPI: 2480 x 3508 pixels
    A4_WIDTH, A4_HEIGHT = 2480, 3508
    SAFE_MARGIN_PX = 60  # ~5mm safe zone
    # Instead of starting at 0,0:
    A4_WIDTH = A4_WIDTH - (SAFE_MARGIN_PX * 2)
    A4_HEIGHT = A4_HEIGHT - (SAFE_MARGIN_PX * 2)

# Now, when you calculate your layout, use usable_w/h 
# and always add SAFE_MARGIN_PX to your final x and y.
# final_x = calculated_x + SAFE_MARGIN_PX
# final_y = calculated_y + SAFE_MARGIN_PX

    collage = Image.new('RGB', (A4_WIDTH, A4_HEIGHT), (255, 255, 255))
    bordered_collage = None

    # # Get up to 4 image paths from the master folder
    # image_files = [os.path.join(master_dir, f) for f in os.listdir(master_dir)
    #                if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    # image_files = sorted(image_files)[:images_per_page]
    import os
    import re

    # Get all image files
    image_files = [
        os.path.join(master_dir, f)
        for f in os.listdir(master_dir)
        if f.lower().endswith(('.png', '.jpg', '.jpeg'))
    ]

    # Sort files (same as your current logic)
    image_files = sorted(image_files)

    # Function to extract group name
    def extract_group(filename):
        match = re.search(r'group-(.*?)\s+place-', filename)
        return match.group(1).strip() if match else None

    # Determine the first group
    first_group = None
    grouped_files = []

    for file in image_files:
        group = extract_group(os.path.basename(file))
        
        if group is None:
            continue
        
        if first_group is None:
            first_group = group
        
        if group == first_group:
            grouped_files.append(file)

    # Optional: limit to images_per_page
    grouped_files = grouped_files[:images_per_page]    

    image_files = grouped_files
    print(f"[Collage] Found {len(image_files)} images: {image_files}")
    for i in image_files:
        print('     Group: ',i)

    if not image_files:
        print("[Collage] No images found in master folder.")
        return None

    # Calculate grid (2x2)
    grid_rows, grid_cols = 2, 2
    cell_width = A4_WIDTH // grid_cols
    cell_height = A4_HEIGHT // grid_rows
    print(f"[Collage] Grid: {grid_rows}x{grid_cols}, cell size: {cell_width}x{cell_height}")

    # Precompute the best orientation for each image to maximize height in the cell
    processed_imgs = []
    box_sizes = []  # To store (x, y, w, h) for each image
    # Prepare a list of place_logo_paths for each image (QR code path)
    place_logo_paths = []
    rotate_90 = False  # Default value, will be set based on the first image
    for idx, img_path in enumerate(image_files):
        print(f"[Collage] Processing image {idx+1}: {img_path}")
        img = Image.open(img_path)
        orig_w, orig_h = img.size
        print(f"[Collage] Original size: {orig_w}x{orig_h}")
        if orig_w > orig_h:
            print('Image is landscape, rotating 90 degrees to portrait for better fit')
            img = img.rotate(90, expand=True)
            rotate_90 = True
            print('rotate_90 set to:', rotate_90)
            orig_w, orig_h = img.size
            print(f"[Collage] Rotated landscape image to portrait: {orig_w}x{orig_h}")
        scale = min(cell_width / orig_w, cell_height / orig_h)
        w1, h1 = int(orig_w * scale), int(orig_h * scale)
        print(f"[Collage] Resizing to fit cell: {w1}x{h1}")
        img = img.resize((w1, h1), Image.Resampling.LANCZOS)
        processed_imgs.append(img)
        # Find the QR code path for this image using robust matching
        qr_dir = os.path.join(os.getcwd(), 'media', 'image_cards', 'qr')
        qr_path = find_matching_qr(img_path, qr_dir)
        place_logo_paths.append(qr_path)
        # Delete the file after loading
        try:
            os.remove(img_path)
            print(f"[Collage] Deleted used master image: {img_path}")

        except Exception as e:
            print(f"[Collage] Failed to delete {img_path}: {e}")

    # Now, for each row, set all images to the same height (max possible for the row)
    for row in range(grid_rows):
        print(f"[Collage] Arranging row {row+1}")
        row_imgs = processed_imgs[row*grid_cols:(row+1)*grid_cols]
        if not row_imgs:
            continue
        min_h = min(img.height for img in row_imgs)
        print(f"[Collage] Row {row+1} min height: {min_h}")
        for col, img in enumerate(row_imgs):
            if img.height != min_h:
                scale = min_h / img.height
                new_w = int(img.width * scale)
                print(f"[Collage] Resizing image in row {row+1}, col {col+1} to {new_w}x{min_h}")
                img = img.resize((new_w, min_h), Image.Resampling.LANCZOS)
                row_imgs[col] = img
            x = col * cell_width + (cell_width - img.width) // 2
            y = row * cell_height + (cell_height - min_h) // 2
            print(f"[Collage] Pasting image at ({x},{y})")
            collage.paste(img, (x, y))
            # Record box size for border-only version
            box_sizes.append((x, y, img.width, img.height))

    # Save in media/image_cards/a4_collages using Django MEDIA_ROOT
    try:
        from django.conf import settings
        media_root = settings.MEDIA_ROOT
    except ImportError:
        media_root = os.path.join(os.getcwd(), 'media')
    a4_dir = os.path.join(media_root, 'image_cards', 'a4_collages')
    os.makedirs(a4_dir, exist_ok=True)
    if output_path is None:
        unique_id = datetime.now().strftime('%b %d %Y - %I %M %S %p')

        
    else:
        unique_id = datetime.now().strftime('%b %d %Y - %I %M %S %p')

    output_path = os.path.join(a4_dir, f'{first_group} {unique_id} Front.png')
    collage.save(output_path)

    
    print(f"[Collage] A4 collage saved to {output_path}")

    # Optionally, also save a bordered version with the same image sizes
    bordered_path = None
    borders_only_path = None

    if also_save_bordered:
        pass
        # print(f"[Collage] Calling save_bordered_a4_collage with border_px={border_px}")
        # bordered_path = save_borders_and_text_a4_collage_from_sizes(box_sizes, None, border_px=border_px)
    if also_save_borders_only:
        print(f"[Collage] Calling save_borders_only_a4_collage_from_sizes with border_px={border_px}")
        borders_only_path = save_borders_only_a4_collage_from_sizes(box_sizes, None, border_px)
        # Example: generate a text label for each box (optional, can be removed or customized)
        texts = ["__postcard__"] * len(box_sizes)
        front_path = output_path
        output_path = os.path.join(a4_dir, f'{first_group} {unique_id} Back.png')
        front_img = Image.open(front_path)
        # rotate_90 = front_img.width > front_img.height
        # print('is it rotating 90 degrees?', rotate_90)
        front_img.close()
        save_borders_and_text_a4_collage_from_sizes(box_sizes, texts,output_path=output_path, border_px=border_px, rotate_90=rotate_90,place_logo_paths=place_logo_paths)

    if also_save_bordered and also_save_borders_only:
        return output_path, bordered_path, borders_only_path
    elif also_save_bordered:
        return output_path, bordered_path
    elif also_save_borders_only:
        return output_path, borders_only_path
    else:
        return output_path

def save_borders_only_a4_collage_from_sizes(box_sizes, output_path=None, border_px=30):
    return
    """
    Given a list of box sizes/positions [(x, y, w, h), ...], save an A4 collage with only the borders (empty boxes) at those positions/sizes.
    The border is drawn inside the box (inset), not outside.
    """
    from PIL import ImageDraw
    print(f"[Borders Only Collage] Creating A4 collage with only borders from box sizes. border_px={border_px}")
    # A4 size at 300 DPI: 2480 x 3508 pixels
    A4_WIDTH, A4_HEIGHT = 2480, 3508
    SAFE_MARGIN_PX = 60  # ~5mm safe zone
    # Instead of starting at 0,0:
    A4_WIDTH = A4_WIDTH - (SAFE_MARGIN_PX * 2)
    A4_HEIGHT = A4_HEIGHT - (SAFE_MARGIN_PX * 2)
    border_color = (0, 0, 0)
    border_thickness = border_px
    borders_collage = Image.new('RGB', (A4_WIDTH, A4_HEIGHT), (255, 255, 255))
    draw = ImageDraw.Draw(borders_collage)
    for idx, (x, y, w, h) in enumerate(box_sizes):
        # Draw rectangle (border only, no fill, no image), border goes inward
        # Draw a single thin rectangle border (avoid thick black outline)
        draw.rectangle([
            (x, y),
            (x + w - 1, y + h - 1)
        ], outline=border_color, width=1)
        print(f"[Borders Only Collage] Drew border at ({x},{y}) size {w}x{h} (inset)")
    try:
        from django.conf import settings
        media_root = settings.MEDIA_ROOT
    except ImportError:
        media_root = os.path.join(os.getcwd(), 'media')
    a4_dir = os.path.join(media_root, 'image_cards', 'a4_collages')
    os.makedirs(a4_dir, exist_ok=True)
    if output_path is None:
        unique_id = datetime.now().strftime('%b %d %Y - %I %M %S %p')
        output_path = os.path.join(a4_dir, f'a4-collage-borders-only-{unique_id}.png')
    borders_collage.save(output_path)
    print(f"[Borders Only Collage] Borders-only A4 collage saved to {output_path}")
    return output_path

def save_borders_and_text_a4_collage_from_sizes(box_sizes, texts='this is a very long texts', output_path=None, border_px=30, font_path=None, font_size=120, text_color=(0,0,0), rotate_90=False, place_logo_paths=None):
    """
    Given a list of box sizes/positions [(x, y, w, h), ...] and a list of strings, save an A4 collage with only the borders (empty boxes) at those positions/sizes and the given string centered in each box.
    """
    from PIL import ImageDraw, ImageFont
    print(f"[Borders+Text Collage] Creating A4 collage with borders and text. border_px={border_px}")
    # A4 size at 300 DPI: 2480 x 3508 pixels

    A4_WIDTH, A4_HEIGHT = 2480, 3508
    SAFE_MARGIN_PX = 60  # ~5mm safe zone
    # Instead of starting at 0,0:
    A4_WIDTH = A4_WIDTH - (SAFE_MARGIN_PX * 2)
    A4_HEIGHT = A4_HEIGHT - (SAFE_MARGIN_PX * 2)    
    border_color = (0, 0, 0)
    border_thickness = border_px
    try:
        borders_collage = Image.new('RGB', (A4_WIDTH, A4_HEIGHT), (255, 255, 255))
        draw = ImageDraw.Draw(borders_collage)
        # Load font robustly
        if font_path is None:
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except Exception:
                font = ImageFont.load_default()
        else:
            font = ImageFont.truetype(font_path, font_size)
        # place_logo_paths is now a direct argument
        print('enumerating box sizes')
        for idx, box in enumerate(box_sizes):
            print(' enumerating started')
            if not (isinstance(box, (list, tuple)) and len(box) == 4):
                print(f"    [Borders+Text Collage] Skipping invalid box_sizes entry at idx {idx}: {box}")
                continue
            x, y, w, h = box
            # Draw a single thin rectangle border (avoid thick black outline)
            draw.rectangle([
                (x, y),
                (x + w - 1, y + h - 1)
            ], outline=border_color, width=1)
            # Draw text centered in the box, rotated if requested
            if texts and idx < len(texts):
                print('     creating special marker for postcard layout')
                # Special marker for postcard layout
                if texts[idx] == '__postcard__':
                    # Try to set posted_name for QR code lookup
                    posted_name = None
                    if hasattr(texts, '__getitem__') and hasattr(texts, '__len__') and len(texts) == len(box_sizes):
                        if isinstance(texts, list) and idx < len(texts):
                            try:
                                posted_name = texts[idx+1] if isinstance(texts[idx+1], str) else None
                            except Exception:
                                posted_name = None
                    if not posted_name:
                        if isinstance(box, (list, tuple)) and len(box) >= 5:
                            posted_name = box[4]
                    if posted_name:
                        setattr(borders_collage, 'posted_name', 1)
                    else:
                        pass
                    # Pass place_logo_path if available
                    place_logo_path = None
                    print('if place_logo_paths')
                    if place_logo_paths and idx < len(place_logo_paths):
                        place_logo_path = place_logo_paths[idx]
                        print('Yest place logo path')
                    print('Drawing postcards layouts')
                    _draw_postcard_layout(borders_collage, x, y, w, h, rotate_90, place_logo_path=place_logo_path)
                    # unique_id = datetime.now().strftime('%b %d %Y - %I %M %S %p')
                    # unique_id = str(unique_id)
                    # safe_id = str(unique_id)
                    # safe_id = safe_id.replace(",", "")
                    # safe_id = safe_id.replace(":", "")
                    # safe_id = safe_id.replace("  ", " ")
                    # safe_id = safe_id.replace(" ", " ")       
                    # dirbase_path = os.path.join(media_root, 'image_cards', 'a4_collages')
                    # svg_path = os.path.join(dirbase_path, f'{safe_id}-.svg')    
                    # 2. Immediately update the SVG file
                    add_cut_rect_to_svg(f'{output_path}.svg', x, y, w, h, A4_WIDTH, A4_HEIGHT)                    
                    print('Checking if has attribute posted_name')
                    if hasattr(borders_collage, 'posted_name'):
                        print('     Has attribute')
                        delattr(borders_collage, 'posted_name')
                    continue
                elif texts[idx] is not None:
                    print('checking if text is not none')
                    print('     text is not none')
                    text = str(texts[idx])
                    # Use font.getsize for text size calculation (Pillow >=8.0.0)
                    try:
                        text_w, text_h = font.getsize(text)
                    except AttributeError:
                        bbox = font.getbbox(text)
                        text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
                    # Always render text without rotating 90 degrees
                    from PIL import Image as PILImage
                    text_img = PILImage.new('RGBA', (text_w, text_h), (255, 255, 255, 0))
                    text_draw = ImageDraw.Draw(text_img)
                    text_draw.text((0, 0), text, fill=text_color + ((255,) if len(text_color) == 3 else ()), font=font)
                    text_x = x + (w - text_w) // 2
                    text_y = y + (h - text_h) // 2
                    borders_collage.paste(text_img, (text_x, text_y), text_img)
                    print(f"[Borders+Text Collage] Drew border and text '{text}' at ({x},{y}) size {w}x{h} (inset)")
                else:
                    print(f"[Borders+Text Collage] Drew border at ({x},{y}) size {w}x{h} (inset)")
            else:
                print(f"    [Borders+Text Collage] Drew border at ({x},{y}) size {w}x{h} (inset)")
        # Do not rotate the whole image, only the text is rotated now
        try:
            from django.conf import settings
            media_root = settings.MEDIA_ROOT
        except ImportError:
            media_root = os.path.join(os.getcwd(), 'media')
        a4_dir = os.path.join(media_root, 'image_cards', 'a4_collages')
        os.makedirs(a4_dir, exist_ok=True)
        if output_path is None:
            print(' Output is None, creating unique id')
            # Use a more readable date and time format, e.g., 'Jan 1, 2026 - 03 45 PM'
            unique_id = datetime.now().strftime('%b %d %Y - %I %M %S %p')
            unique_id = str(unique_id)
            safe_id = str(unique_id)
            safe_id = safe_id.replace(",", "")
            safe_id = safe_id.replace(":", "")
            safe_id = safe_id.replace("  ", " ")
            safe_id = safe_id.replace(" ", " ")         
            
            # unique_id = datetime.now().strftime('%b %d %Y - %I %M %p')
            # # Replace spaces and commas for filename safety
            # safe_id = unique_id.replace(",", "").replace(":", "").replace("  ", " ").replace(" ", "_")
            output_path = os.path.join(a4_dir, f'{safe_id}-a4-collage-borders-text.png')
        borders_collage.save(output_path)
        print(f"[Borders+Text Collage] Borders+text A4 collage saved to {output_path}")
        return output_path
    except Exception as e:
        import traceback

        print("[Borders+Text Collage] Error:", e)
        traceback.print_exc()
        return None        

