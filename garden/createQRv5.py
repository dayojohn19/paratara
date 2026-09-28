import os
# 1. Import your new engine
from garden.wordart_engine import WordArtEngine

# 2. Define a path to a font you like
WORDART_FONT_PATH = "garden/assets/fonts/Anron/Anton-Regular.ttf" # Exampleimport os
import random
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO

import qrcode
import requests
from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

# try:
#     from garden.wordart3 import postcard_title
# except ImportError:
#     from wordart3 import postcard_title


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


# Map a collection theme to a postcard_title preset.
THEME_TO_PRESET = {
    "black": "poster",        # bold black — big bold poster
    "gold": "editorial",      # gold — elegant small caps
    "champagne": "editorial",
    "emerald": "minimal",     # emerald — clean, modern
    "sapphire": "editorial",
    "ruby": "vintage",        # ruby — classic ornamental
    "rose-gold": "editorial",
    "platinum": "minimal",
    "pearl": "editorial",
    "bronze": "vintage",
}

# Map a collection theme to a postcard_title palette name.
THEME_TO_PALETTE = {
    "black": "ink_white",
    "gold": "ivory_navy",
    "champagne": "ivory_navy",
    "emerald": "white_forest",
    "sapphire": "slate_copper",
    "ruby": "cream_burgundy",
    "rose-gold": "blush_plum",
    "platinum": "ink_white",
    "pearl": "blush_plum",
    "bronze": "warm_charcoal",
}


DEFAULT_TITLE_PRESET = "editorial"
DEFAULT_TITLE_PALETTE = "auto"


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
    # --- new for postcard_title ---
    title_preset: str = ""            # "" → derive from theme
    title_palette: str = ""           # "" → derive from theme


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


def pick_title_preset(collection_obj, override=""):
    if override:
        return override
    theme_key = _normalized_theme(collection_obj)
    if theme_key and theme_key in THEME_TO_PRESET:
        return THEME_TO_PRESET[theme_key]
    return DEFAULT_TITLE_PRESET


def pick_title_palette(collection_obj, override=""):
    if override:
        return override
    theme_key = _normalized_theme(collection_obj)
    if theme_key and theme_key in THEME_TO_PALETTE:
        return THEME_TO_PALETTE[theme_key]
    return DEFAULT_TITLE_PALETTE


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
# TITLE RENDERING (postcard_title integration)
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

# In createQR.py



# 3. Update the _build_title_overlay function
def _build_title_overlay(image, collection_obj, custom_title, config):
    """Render the WordArt title overlay using the custom WordArtEngine."""
    main_title, subtitle = split_title_and_subtitle(collection_obj, custom_title)
    if not main_title:
        return None

    max_width = int(image.width * config.title_max_width_ratio)
    max_height = int(image.height * config.title_max_height_ratio)

    # Define your style based on theme
    theme_key = _normalized_theme(collection_obj)
    # Example: map themes to styles
    style = "outline"
    if theme_key == "gold":
        style = "gradient"
    elif theme_key == "emerald":
        style = "shadow"

    # Initialize engine
    engine = WordArtEngine(WORDART_FONT_PATH)

    # Render the art
    title_art = engine.render(
        text=main_title.upper(),
        canvas_size=(max_width * 2, max_height * 2),
        style=style,
        font_size=100,
         
        fill_color=tuple(int(theme_color_for_image(collection_obj, image)[i:i+2], 16) for i in (1, 3, 5)), # Use theme color
        outline_color=(0, 0, 0),
        outline_width=4,
    )
    
    # Fit the art to the card
    title_art = fit_wordart_title(title_art, max_width, max_height)
    
    return title_art

# The rest of your draw_title function can stay the same,
# as it just calls _build_title_overlay.

def draw_title(image, collection_obj, custom_title="", config=QRImageConfig()):
    """Composite the postcard title on the card. Returns the border color."""
    title_art = _build_title_overlay(image, collection_obj, custom_title, config)

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


def draw_footer(image, collection_obj):
    scale = image_scale(image)
    footer_text = f"{collection_obj.collectionGroup}".strip()
    if not footer_text:
        return

    draw = ImageDraw.Draw(image)
    draw.text(
        (image.width - 20, image.height - 20),
        text=footer_text,
        fill="#FFFFFF",
        font=load_subtitle_font(scale),
        anchor="rs",
        stroke_width=max(1, int(2 * scale)),
        stroke_fill="#000000",
    )


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
    return (f"group-{collection_obj.collectionGroup} "
            f"place-{collection_obj.collectionPlace} {slug}")


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


def CreateQRCode(request, collectionObj, appDownloadLink,
                 customTitle="", include_heading_title=True, paste_qr=True):
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
    print(f"[CreateQRCode] Setting collectionGoogleDriveURL to: "
          f"{saved_paths['relative_master_path']}")
    print(f"[CreateQRCode] Setting collectionLocalFile to collectionPicture: "
          f"{collectionObj.collectionPicture}")

    update_collection_image_fields(collectionObj, saved_paths)
    return saved_paths