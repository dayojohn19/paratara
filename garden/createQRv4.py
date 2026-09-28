import math
import os
import random
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO

import qrcode
import requests
from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

try:
    from pythonWordArt import pyWordArt
except ImportError:
    pyWordArt = None


BASE_QR_URL = "https://www.paratara.com/garden/qr"
DEFAULT_FONT_PATH = "garden/assets/fonts/helvetica-255/helvetica-rounded-bold-5871d05ead8de.otf"
DEFAULT_FONT_DIR = "garden/assets/fonts"


THEME_COLOR_MAP = {
    "black": "#000000",
    "gold": "#FFD700",
    "champagne": "#F7E7CE",
    "emerald": "#50C878",
    "sapphire": "#0F52BA",
    "ruby": "#E0115F",
    "rose-gold": "#B76E79",
    "platinum": "#E5E4E2",
    "pearl": "#FDEEF4",
    "bronze": "#CD7F32",
}


# WordArt styles (0-29) mapped from collection theme.
# See pythonWordArt.Styles for the full list.
THEME_TO_WORDART_STYLE = {
    "black": 0,
    "gold": 5,
    "champagne": 3,
    "emerald": 7,
    "sapphire": 9,
    "ruby": 12,
    "rose-gold": 14,
    "platinum": 2,
    "pearl": 4,
    "bronze": 11,
}
DEFAULT_WORDART_STYLE = 5


@dataclass(frozen=True)
class QRImageConfig:
    output_max_px: int = 2000
    qr_error_correction: int = qrcode.constants.ERROR_CORRECT_M
    qr_box_size: int = 10
    qr_border: int = 2
    qr_size_ratio: float = 2.75
    qr_size_multiplier: float = 0.90
    title_max_width_ratio: float = 0.80
    title_max_height_ratio: float = 0.20
    title_font_height_ratio: float = 0.11
    title_min_font_size: int = 18
    title_spacing: int = 8
    wordart_style: int = -1       # -1 → derive from theme
    wordart_font_size: int = 100  # pythonWordArt font size
    wordart_canvas_w: int = 1754
    wordart_canvas_h: int = 1240


# ---------------------------------------------------------------------------
# COLOR / THEME HELPERS
# ---------------------------------------------------------------------------
def get_contrast_color(pil_img, vivid=False):
    """Return black or white, or a vivid inverse, based on average image brightness."""
    img = pil_img.convert("RGB").resize((1, 1))
    r, g, b = img.getpixel((0, 0))

    if vivid:
        return "#{:02x}{:02x}{:02x}".format(255 - r, 255 - g, 255 - b)

    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return "#000000" if luminance > 0.5 else "#FFFFFF"


def _normalized_theme(collection_obj):
    theme = getattr(collection_obj, "collectionTheme", None)
    if not theme:
        return None
    return str(theme).strip().lower()


def theme_color_for_image(collection_obj, image):
    theme_key = _normalized_theme(collection_obj)
    if not theme_key:
        return get_contrast_color(image)

    if theme_key in THEME_COLOR_MAP:
        return THEME_COLOR_MAP[theme_key]
    if theme_key.startswith("#"):
        return theme_key
    return "#000000"


def pick_wordart_style(collection_obj, override=-1):
    if override >= 0:
        return override
    theme_key = _normalized_theme(collection_obj)
    if theme_key and theme_key in THEME_TO_WORDART_STYLE:
        return THEME_TO_WORDART_STYLE[theme_key]
    return DEFAULT_WORDART_STYLE


# ---------------------------------------------------------------------------
# FONT HELPERS  (kept for QR-side rendering)
# ---------------------------------------------------------------------------
def load_font_with_fallback(font_path, font_size):
    try:
        return ImageFont.truetype(font_path, font_size)
    except Exception:
        return ImageFont.truetype(DEFAULT_FONT_PATH, font_size)


def find_font_paths(font_dir=DEFAULT_FONT_DIR):
    fonts = []
    for root, _, files in os.walk(font_dir):
        for file_name in files:
            if file_name.lower().endswith((".ttf", ".otf")):
                fonts.append(os.path.join(root, file_name))
    return fonts


def get_random_font_path(font_dir=DEFAULT_FONT_DIR):
    fonts = find_font_paths(font_dir)
    if not fonts:
        raise FileNotFoundError(f"No .ttf or .otf fonts found in {font_dir}.")
    return random.choice(fonts)


def get_random_font(font_dir=DEFAULT_FONT_DIR, font_size=90):
    return ImageFont.truetype(get_random_font_path(font_dir), font_size)


# ---------------------------------------------------------------------------
# QR BUILDING
# ---------------------------------------------------------------------------
def build_qr_url(collection_obj, base_url=BASE_QR_URL):
    return f"{base_url.rstrip('/')}/{collection_obj.collectionUniqueID}/"


def create_qr_image(data, config=QRImageConfig()):
    qr_builder = qrcode.QRCode(
        error_correction=config.qr_error_correction,
        box_size=config.qr_box_size,
        border=config.qr_border,
    )
    qr_builder.add_data(data)
    qr_builder.make(fit=True)
    return qr_builder.make_image(fill_color="black", back_color="white").convert("RGBA")


# ---------------------------------------------------------------------------
# IMAGE LOADING
# ---------------------------------------------------------------------------
def load_remote_image(url, timeout=20):
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return Image.open(BytesIO(response.content))


def prepare_place_image(image, config=QRImageConfig()):
    place_image = ImageOps.exif_transpose(image).convert("RGBA")
    place_image.thumbnail((config.output_max_px, config.output_max_px),
                          Image.Resampling.LANCZOS)
    return ImageEnhance.Sharpness(place_image).enhance(1.5)


DEFAULT_FALLBACK_COLOR = "#CCCCCC"
DEFAULT_FALLBACK_SIZE = (1200, 800)


def create_fallback_image(size=DEFAULT_FALLBACK_SIZE, color=DEFAULT_FALLBACK_COLOR):
    return Image.new("RGBA", size, color)


def image_scale(image):
    return max(0.5, min(image.width, image.height) / 800.0)


# ---------------------------------------------------------------------------
# QR POSITION / SIZE
# ---------------------------------------------------------------------------
def qr_display_size(place_image, config=QRImageConfig()):
    shortest_side = min(place_image.width, place_image.height)
    size = int((shortest_side / config.qr_size_ratio) * config.qr_size_multiplier)
    return max(1, size)


def resize_qr_for_card(qr_image, place_image, config=QRImageConfig()):
    size = qr_display_size(place_image, config)
    return qr_image.resize((size, size), resample=Image.Resampling.NEAREST)


def qr_position(place_image, qr_image):
    scale = image_scale(place_image)
    padding = max(16, int(24 * scale))
    return padding, place_image.height - qr_image.height - padding


# ---------------------------------------------------------------------------
# TITLE + SUBTITLE PARSING
# ---------------------------------------------------------------------------
def split_title_and_subtitle(collection_obj, custom_title=""):
    """Return (main_title, subtitle). Subtitle may be None."""
    if custom_title:
        cleaned = custom_title.replace("\\n", "\n")
        parts = cleaned.split("\n", 1)
        main_title = parts[0].strip()
        subtitle = parts[1].strip() if len(parts) > 1 and parts[1].strip() else None
        return main_title, subtitle

    place = collection_obj.collectionPlace
    main_title = (getattr(place, "placeName", "") or "").strip()
    province = (getattr(place, "placeProvince", "") or "").strip()
    return main_title, (province or None)


# ---------------------------------------------------------------------------
# TITLE RENDERING  (pythonWordArt integration)
# ---------------------------------------------------------------------------
def trim_transparent_padding(image):
    bbox = image.getbbox()
    if not bbox:
        return image
    return image.crop(bbox)


def fit_wordart_title(title_image, max_width, max_height):
    title_image = trim_transparent_padding(title_image)
    if title_image.width <= 0 or title_image.height <= 0:
        return title_image

    scale = min(max_width / title_image.width,
                max_height / title_image.height,
                1)
    size = (
        max(1, int(title_image.width * scale)),
        max(1, int(title_image.height * scale)),
    )
    return title_image.resize(size, Image.Resampling.LANCZOS)


def _render_wordart(title, style_index, font_size, canvas_w, canvas_h):
    """Render WordArt using pythonWordArt and return a PIL RGBA image."""
    if pyWordArt is None:
        raise ImportError(
            "pythonWordArt is not installed. Run: pip install pythonWordArt"
        )

    w = pyWordArt()
    w.canvasWidth = canvas_w
    w.canvasHeight = canvas_h

    # The style index is 0-29. If out of range, clamp.
    style = w.Styles[style_index % len(w.Styles)]
    w.WordArt(title, style, str(font_size))

    # toBufferIO() returns a file-like object that PIL can open directly.
    return Image.open(w.toBufferIO()).convert("RGBA")


def _build_title_overlay(image, collection_obj, custom_title, config):
    """Render the WordArt title overlay using pythonWordArt."""
    main_title, subtitle = split_title_and_subtitle(collection_obj, custom_title)
    if not main_title:
        return None

    max_width = int(image.width * config.title_max_width_ratio)
    max_height = int(image.height * config.title_max_height_ratio)

    style_index = pick_wordart_style(collection_obj, config.wordart_style)

    # Render WordArt. If subtitle exists, combine them with a line break
    # so both appear in the same WordArt block.
    display_text = main_title
    if subtitle:
        display_text = f"{main_title}\n{subtitle}"

    title_art = _render_wordart(
        display_text,
        style_index=style_index,
        font_size=config.wordart_font_size,
        canvas_w=config.wordart_canvas_w,
        canvas_h=config.wordart_canvas_h,
    )

    title_art = fit_wordart_title(title_art, max_width, max_height)
    if title_art.width == 0 or title_art.height == 0:
        return None
    return title_art


def draw_title(image, collection_obj, custom_title="", config=QRImageConfig()):
    """Composite the WordArt title on the card. Returns the border color."""
    try:
        title_art = _build_title_overlay(image, collection_obj, custom_title, config)
    except Exception as e:
        print(f"[draw_title] pythonWordArt failed: {e}. Skipping title.")
        title_art = None

    if title_art is not None:
        vertical_offset = int(image.height * 0.035)
        position = (
            max(0, (image.width - title_art.width) // 2),
            min(
                max(10, int(image.height * 0.025)) + vertical_offset,
                max(10, image.height - title_art.height - 10),
            ),
        )
        image.alpha_composite(title_art, dest=position)

    return theme_color_for_image(collection_obj, image)


# ---------------------------------------------------------------------------
# BORDER + FOOTER
# ---------------------------------------------------------------------------
def draw_border(image, color):
    draw = ImageDraw.Draw(image)
    draw.rectangle(
        [(10, 10), (image.width - 10, image.height - 10)],
        fill=None,
        outline=color,
        width=2,
    )


def load_subtitle_font(scale):
    try:
        return get_random_font(font_size=max(13, int(18 * scale)))
    except Exception:
        return ImageFont.truetype(DEFAULT_FONT_PATH, max(12, int(17 * scale)))


def star_points(cx, cy, outer_r, inner_r, rotation_deg=0):
    """10 (x, y) points for a 5-pointed star.
    First outer tip is at `rotation_deg` (screen coords: y increases down)."""
    pts = []
    for i in range(10):
        r = outer_r if i % 2 == 0 else inner_r
        a = math.radians(rotation_deg + i * 36)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def build_three_star_logo(size=12, fill="#000000",
                          outer_stroke="#FFFFFF", outer_width=4,
                          inner_stroke="#000000", inner_width=2,
                          fatness=0.55, gap_ratio=0.75,
                          drop_shadow=False):
    """Three fat stars in an equilateral triangle, black fill with a
    double stroke (white halo outside, black edge inside)."""
    outer_r = float(size)
    inner_r = outer_r * fatness

    gap = outer_r * gap_ratio
    R = outer_r + gap / math.sqrt(3)

    s3_2 = math.sqrt(3) / 2
    centers = [
        ( R,             0.0),      # right star
        (-R * 0.5,  -R * s3_2),     # upper-left star
        (-R * 0.5,   R * s3_2),     # lower-left star
    ]

    rotations = []
    for i, (cx, cy) in enumerate(centers):
        angles = []
        for j, (ox, oy) in enumerate(centers):
            if i == j:
                continue
            angles.append(math.degrees(math.atan2(oy - cy, ox - cx)))
        a0, a1 = angles
        while a1 - a0 >  180: a1 -= 360
        while a1 - a0 < -180: a1 += 360
        bisector = (a0 + a1) / 2.0
        rotations.append(bisector - 36.0)

    pad = int(math.ceil(outer_width / 2)) + (6 if drop_shadow else 3)
    xs = [c[0] for c in centers]
    ys = [c[1] for c in centers]
    min_x = min(xs) - outer_r - pad
    max_x = max(xs) + outer_r + pad
    min_y = min(ys) - outer_r - pad
    max_y = max(ys) + outer_r + pad

    W = int(math.ceil(max_x - min_x))
    H = int(math.ceil(max_y - min_y))
    ox, oy = -min_x, -min_y

    if drop_shadow:
        from PIL import ImageFilter
        shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sd = ImageDraw.Draw(shadow)
        for (cx, cy), rot in zip(centers, rotations):
            pts = star_points(cx + ox + 2, cy + oy + 3,
                              outer_r, inner_r, rotation_deg=rot)
            sd.polygon(pts, fill=(0, 0, 0, 130))
        shadow = shadow.filter(ImageFilter.GaussianBlur(2))
    else:
        shadow = None

    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if shadow is not None:
        img.alpha_composite(shadow)

    draw = ImageDraw.Draw(img)
    for (cx, cy), rot in zip(centers, rotations):
        pts = star_points(cx + ox, cy + oy, outer_r, inner_r,
                          rotation_deg=rot)
        draw.polygon(pts, fill=None, outline=outer_stroke, width=outer_width)
        draw.polygon(pts, fill=fill, outline=inner_stroke, width=inner_width)

    return img


def draw_footer(image, collection_obj=None):
    """Draw the 3-star cluster in the bottom-right corner."""
    scale = image_scale(image)
    logo = build_three_star_logo(
        size=max(9, int(14 * scale)),
        fill="#000000",
        outer_stroke="#FFFFFF",
        outer_width=max(2, int(4 * scale)),
        inner_stroke="#000000",
        inner_width=max(1, int(2 * scale)),
        fatness=0.55,
        gap_ratio=0.75,
        drop_shadow=False,
    )

    pad = max(16, int(24 * scale))
    pos = (image.width  - logo.width  - pad,
           image.height - logo.height - pad)

    if image.mode != "RGBA":
        base = image.convert("RGBA")
        base.alpha_composite(logo, dest=pos)
        return base

    image.alpha_composite(logo, dest=pos)
    return image


# ---------------------------------------------------------------------------
# CARD COMPOSITION
# ---------------------------------------------------------------------------
def compose_collection_card(
    place_image,
    qr_image,
    collection_obj,
    custom_title="",
    include_title=True,
    paste_qr=True,
    config=QRImageConfig(),
):
    card = prepare_place_image(place_image, config)
    qr_for_card = resize_qr_for_card(qr_image, card, config)

    if paste_qr:
        card.paste(qr_for_card, qr_position(card, qr_for_card))

    border_color = theme_color_for_image(collection_obj, card)
    if include_title:
        border_color = draw_title(card, collection_obj, custom_title, config)

    draw_border(card, border_color)
    draw_footer(card, collection_obj)
    return card, qr_for_card


# ---------------------------------------------------------------------------
# FILE NAMING / SAVING
# ---------------------------------------------------------------------------
def collection_file_slug(collection_obj):
    return f"{collection_obj.collectionName}-{collection_obj.collectionUniqueID}"


def collection_file_prefix(collection_obj):
    slug = collection_file_slug(collection_obj)
    return f"group-{collection_obj.collectionGroup} place-{collection_obj.collectionPlace} {slug}"


def ensure_output_dirs(media_root):
    media_base = os.path.join(media_root, "image_cards")
    paths = {
        "qr": os.path.join(media_base, "qr"),
        "master": os.path.join(media_base, "master"),
    }

    for path in paths.values():
        os.makedirs(path, exist_ok=True)

    return paths


def save_generated_images(collection_obj, card_image, qr_image, media_root):
    output_dirs = ensure_output_dirs(media_root)
    file_prefix = collection_file_prefix(collection_obj)

    qr_path = os.path.join(output_dirs["qr"], f"{file_prefix}-qr.png")
    master_path = os.path.join(output_dirs["master"], f"{file_prefix}-master.png")

    qr_image.save(qr_path, format="PNG")
    card_image.save(master_path, format="PNG", dpi=(300, 300))

    return {
        "qr_path": qr_path,
        "master_path": master_path,
        "relative_master_path": os.path.relpath(master_path, media_root),
    }


def update_collection_image_fields(collection_obj, saved_paths):
    collection_obj.collectionGoogleDriveURL = saved_paths["relative_master_path"]
    collection_obj.collectionLocalFile = collection_obj.collectionPicture
    collection_obj.save()


# ---------------------------------------------------------------------------
# TOP-LEVEL GENERATION
# ---------------------------------------------------------------------------
def generate_collection_card(
    collection_obj,
    custom_title="",
    include_title=True,
    paste_qr=True,
    image_loader=load_remote_image,
    config=QRImageConfig(),
):
    qr_url = build_qr_url(collection_obj)
    qr_image = create_qr_image(qr_url, config)
    try:
        place_image = image_loader(collection_obj.collectionPicture)
    except Exception:
        place_image = create_fallback_image()

    card_image, qr_for_card = compose_collection_card(
        place_image=place_image,
        qr_image=qr_image,
        collection_obj=collection_obj,
        custom_title=custom_title,
        include_title=include_title,
        paste_qr=paste_qr,
        config=config,
    )
    return card_image, qr_for_card


def CreateQRCode(request, collectionObj, appDownloadLink, customTitle="", include_heading_title=True, paste_qr=True):
    """Generate and save collection card images."""
    from django.conf import settings

    card_image, qr_image = generate_collection_card(
        collection_obj=collectionObj,
        custom_title=customTitle,
        include_title=include_heading_title,
        paste_qr=paste_qr,
    )

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    name_slug = collection_file_slug(collectionObj)
    print(f"[CreateQRCode] Saving images for collection: {name_slug} at {timestamp}")

    saved_paths = save_generated_images(
        collection_obj=collectionObj,
        card_image=card_image,
        qr_image=qr_image,
        media_root=settings.MEDIA_ROOT,
    )

    print(f"[CreateQRCode] Saving QR image to: {saved_paths['qr_path']}")
    print(f"[CreateQRCode] Saving master image to: {saved_paths['master_path']}")
    print(f"[CreateQRCode] Setting collectionGoogleDriveURL to: {saved_paths['relative_master_path']}")
    print(f"[CreateQRCode] Setting collectionLocalFile to collectionPicture: {collectionObj.collectionPicture}")

    update_collection_image_fields(collectionObj, saved_paths)
    return saved_paths