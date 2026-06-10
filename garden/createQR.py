import os
import random
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO

import qrcode
import requests
from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

try:
    from garden.wordart3 import postcard_place_text
except ImportError:
    from wordart3 import postcard_place_text


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


@dataclass(frozen=True)
class QRImageConfig:
    output_max_px: int = 2000
    qr_error_correction: int = qrcode.constants.ERROR_CORRECT_M
    qr_box_size: int = 10
    qr_border: int = 2
    qr_size_ratio: float = 2.75
    qr_size_multiplier: float = 0.90
    title_max_width_ratio: float = 0.85
    title_max_height_ratio: float = 0.22
    title_font_height_ratio: float = 0.11
    title_min_font_size: int = 18
    title_spacing: int = 8


def get_contrast_color(pil_img, vivid=False):
    """Return black or white, or a vivid inverse, based on average image brightness."""
    img = pil_img.convert("RGB").resize((1, 1))
    r, g, b = img.getpixel((0, 0))

    if vivid:
        return "#{:02x}{:02x}{:02x}".format(255 - r, 255 - g, 255 - b)

    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return "#000000" if luminance > 0.5 else "#FFFFFF"


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


def load_remote_image(url, timeout=20):
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return Image.open(BytesIO(response.content))


def prepare_place_image(image, config=QRImageConfig()):
    place_image = ImageOps.exif_transpose(image).convert("RGBA")
    place_image.thumbnail((config.output_max_px, config.output_max_px), Image.Resampling.LANCZOS)
    return ImageEnhance.Sharpness(place_image).enhance(1.5)


DEFAULT_FALLBACK_COLOR = "#CCCCCC"
DEFAULT_FALLBACK_SIZE = (1200, 800)


def create_fallback_image(size=DEFAULT_FALLBACK_SIZE, color=DEFAULT_FALLBACK_COLOR):
    """Create a simple solid-color fallback RGBA image when loading fails."""
    return Image.new("RGBA", size, color)


def image_scale(image):
    return max(0.5, min(image.width, image.height) / 800.0)


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


def title_text_for_collection(collection_obj, custom_title=""):
    if custom_title:
        return custom_title.replace("\\n", "\n")

    place = collection_obj.collectionPlace
    return f"{place.placeName}\n{place.placeProvince}"


def theme_color_for_image(collection_obj, image):
    theme = getattr(collection_obj, "collectionTheme", None)
    if not theme:
        return get_contrast_color(image)

    theme_key = str(theme).strip().lower()
    if theme_key in THEME_COLOR_MAP:
        return THEME_COLOR_MAP[theme_key]
    if theme_key.startswith("#"):
        return theme_key
    return "#000000"


def fit_multiline_font(draw, text, font_path, max_width, max_height, start_size, min_size, spacing):
    font_size = start_size
    font = load_font_with_fallback(font_path, font_size)

    while font_size >= min_size:
        font = load_font_with_fallback(font_path, font_size)
        bbox = draw.multiline_textbbox((0, 0), text, font=font, spacing=spacing)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        if text_width <= max_width and text_height <= max_height:
            return font
        font_size -= 2

    return font


def trim_transparent_padding(image):
    bbox = image.getbbox()
    if not bbox:
        return image
    return image.crop(bbox)


def fit_wordart_title(title_image, max_width, max_height):
    title_image = trim_transparent_padding(title_image)
    if title_image.width <= 0 or title_image.height <= 0:
        return title_image

    scale = min(max_width / title_image.width, max_height / title_image.height, 1)
    size = (
        max(1, int(title_image.width * scale)),
        max(1, int(title_image.height * scale)),
    )
    return title_image.resize(size, Image.Resampling.LANCZOS)


def draw_title(image, collection_obj, custom_title="", config=QRImageConfig()):
    title_text = title_text_for_collection(collection_obj, custom_title).replace("\n", " ")
    max_width = int(image.width * config.title_max_width_ratio)
    max_height = int(image.height * config.title_max_height_ratio)

    title_art = postcard_place_text(
        title_text,
        canvas_size=(max(900, max_width * 2), max(260, max_height * 2)),
    )
    title_art = fit_wordart_title(title_art, max_width, max_height)

    position = (int(image.width * 0.025), int(image.height * 0.025))
    image.alpha_composite(title_art, dest=position)

    return theme_color_for_image(collection_obj, image)


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
    """Generate and save collection card images.

    The signature is kept for existing callers. `request`, `appDownloadLink`, and
    `include_heading_title` are currently accepted for compatibility with the
    older view code.
    """
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
