
import os
from io import BytesIO

import requests
from PIL import Image, ImageOps

API_IMBB_KEY = "ca7f3a26f5fb6343337e4a4f02c07b12"
FOLDER_PATH = "image_bank"   # folder with your images
PROCESSED_FOLDER = "image_bank_uploaded"
QUALITY = 75           # desired JPEG quality
MAX_UPLOAD_BYTES = 10 * 1024 * 1024   # 10 MB — Cloudinary free-tier hard limit

try:
    import cloudinary
    import cloudinary.uploader
    cloudinary.config(
        cloud_name="dg6xfou1t",
        api_key="875272749645643",
        api_secret="1KRVTKh6DiluDJB2SIovyFpizd0",
        secure=True,
    )
    CLOUDINARY_AVAILABLE = True
except Exception:
    CLOUDINARY_AVAILABLE = False

def upload_image(image_path):
    with open(image_path, "rb") as file:
        response = requests.post(
            "https://api.imgbb.com/1/upload",
            data={"key": API_IMBB_KEY},
            files={"image": file}
        )
    return response.json()

# create processed folder if not exists
os.makedirs(PROCESSED_FOLDER, exist_ok=True)


def _jpeg_stream_from_file(file_obj):
    file_obj.seek(0)
    with Image.open(file_obj) as img:
        img = ImageOps.exif_transpose(img)

        # JPEG does not support transparency; flatten alpha when needed.
        if img.mode in ("RGBA", "LA"):
            base = Image.new("RGB", img.size, (255, 255, 255))
            alpha = img.getchannel("A")
            base.paste(img.convert("RGB"), mask=alpha)
            img = base
        elif img.mode == "P":
            img = img.convert("RGBA")
            base = Image.new("RGB", img.size, (255, 255, 255))
            alpha = img.getchannel("A")
            base.paste(img.convert("RGB"), mask=alpha)
            img = base
        elif img.mode != "RGB":
            img = img.convert("RGB")

        # Start at the configured quality and step down until under the limit.
        quality = QUALITY
        while True:
            stream = BytesIO()
            img.save(stream, format="JPEG", quality=quality, optimize=True)
            size = stream.tell()
            if size <= MAX_UPLOAD_BYTES or quality <= 10:
                break
            quality -= 10
            print(f"Image {size} bytes > {MAX_UPLOAD_BYTES}, retrying at quality={quality}")

        stream.seek(0)
        return stream


def _upload_prepared_image(jpeg_stream,folder_name, name_hint="upload.jpg"):
    if CLOUDINARY_AVAILABLE:
        print('Uploading to Cloudinary...')
        res = cloudinary.uploader.upload(jpeg_stream, folder=folder_name,resource_type='image')
        return res.get('secure_url') or res.get('url')

    response = requests.post(
        "https://api.imgbb.com/1/upload",
        data={"key": API_IMBB_KEY},
        files={"image": (name_hint, jpeg_stream, "image/jpeg")}
    )
    r = response.json()
    if r.get("success") is True:
        return r["data"]["url"]
    return None


def _process_one_file(file_obj, folder_name):
    """Compress and upload a single file; returns URL or None."""
    try:
        name_root, _ = os.path.splitext(getattr(file_obj, "name", "upload"))
        stream = _jpeg_stream_from_file(file_obj)
        return _upload_prepared_image(stream, folder_name,name_hint=f"{name_root}.jpg")
    except Exception as e:
        print(f"Upload failed for {getattr(file_obj, 'name', 'unknown file')}: {e}")
        return None


def get_uploaded_image_urls(files,folder_name, max_workers=6):
    """Upload request.FILES images in parallel to Cloudinary/ImgBB.

    max_workers=6 keeps Cloudinary happy while cutting total time ~6x
    compared to sequential uploads.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    results = [None] * len(files)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_idx = {executor.submit(_process_one_file, f, folder_name): i for i, f in enumerate(files)}
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            results[idx] = future.result()

    return [url for url in results if url]

def get_all_image_urls():
    print('starting upload to imbb')
    urls = []
 
    for filename in os.listdir(FOLDER_PATH):
        print(f'processing file: {filename}')
        full_path = os.path.join(FOLDER_PATH, filename)

        # skip non-image files
        if not os.path.isfile(full_path) or not filename.lower().endswith((".png", ".jpg", ".jpeg")):
            continue

        # open image and prepare optimized JPEG in memory
        uploaded_url = None
        try:
            with open(full_path, "rb") as file:
                name_root, _ = os.path.splitext(filename)
                stream = _jpeg_stream_from_file(file)
                uploaded_url = _upload_prepared_image(stream, name_hint=f"{name_root}.jpg")
        except Exception as e:
            print(f"Upload failed for {filename}: {e}")

        if uploaded_url:
            urls.append(uploaded_url)

        # remove original file
        try:
            os.remove(full_path)
        except Exception:
            pass
        print(f"Processed and uploaded: {filename}")
    return urls


def get_all_image_urls_old(request=None):
    urls = []

    for filename in os.listdir(FOLDER_PATH):
        full_path = os.path.join(FOLDER_PATH, filename)

        if not os.path.isfile(full_path):
            continue

        if not filename.lower().endswith((".png", ".jpg", ".jpeg")):
            continue

        with open(full_path, "rb") as file:
            response = requests.post(
                "https://api.imgbb.com/1/upload",
                data={"key": API_IMBB_KEY},
                files={"image": file}
            )
            r = response.json()
            if r.get("success") is True:
                urls.append(r["data"]["url"])     # ImgBB URL

    return urls



def upload_all_images(request=None):
    # Loop all files inside folder
    for filename in os.listdir(FOLDER_PATH):

        # Build full path
        full_path = os.path.join(FOLDER_PATH, filename)

        # Ignore non-files
        if not os.path.isfile(full_path):
            continue

        # Ignore non-images (optional)
        if not filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
            continue

        print(f"Uploading: {filename} ...")

        result = upload_image(full_path)
        print(result)          # Show API response
        print("-" * 50)


if __name__ == "__main__":
    upload_all_images()
