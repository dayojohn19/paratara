#!/usr/bin/env python3
"""
Simple image optimizer:
- Walks configured image folders
- Converts images to WebP and/or recompresses JPEG/PNG
- Skips already-optimized images
Usage:
  python tools/optimize_images.py --folders image_bank imageuploads --quality 75 --webp
"""
from PIL import Image, UnidentifiedImageError
import os
import argparse
from pathlib import Path

DEFAULT_FOLDERS = [
    'image_bank', 'image_bank_uploaded', 'imageuploads', 'imageuploaded', 'UserProfileImages2', 'storyimages'
]

def optimize_image(path: Path, quality=75, make_webp=True):
    try:
        with Image.open(path) as im:
            im_format = im.format
            # Skip tiny files
            if path.stat().st_size < 2000:
                return False
            # Convert/resize if very large
            max_dim = 1920
            if max(im.size) > max_dim:
                ratio = max_dim / max(im.size)
                new_size = (int(im.width * ratio), int(im.height * ratio))
                im = im.resize(new_size, Image.LANCZOS)

            changed = False
            if make_webp:
                webp_path = path.with_suffix('.webp')
                if not webp_path.exists() or webp_path.stat().st_size > path.stat().st_size:
                    im.save(webp_path, 'WEBP', quality=quality, method=6)
                    changed = True

            if im_format in ('JPEG', 'JPG', 'PNG'):
                # Re-save with quality/compression
                tmp = path.with_suffix(path.suffix + '.opt')
                save_kwargs = {}
                if im_format in ('JPEG', 'JPG'):
                    save_kwargs['quality'] = quality
                    save_kwargs['optimize'] = True
                    save_kwargs['progressive'] = True
                elif im_format == 'PNG':
                    save_kwargs['optimize'] = True
                    save_kwargs['compress_level'] = 6
                try:
                    im.save(tmp, im_format, **save_kwargs)
                    if tmp.stat().st_size < path.stat().st_size:
                        tmp.replace(path)
                        changed = True
                    else:
                        tmp.unlink()
                except Exception:
                    if tmp.exists():
                        tmp.unlink()
            return changed
    except UnidentifiedImageError:
        return False
    except Exception:
        return False


def walk_and_optimize(base: Path, quality=75, make_webp=True):
    changed_count = 0
    for root, dirs, files in os.walk(base):
        for f in files:
            p = Path(root) / f
            if p.suffix.lower() in ('.jpg', '.jpeg', '.png', '.webp'):
                if optimize_image(p, quality=quality, make_webp=make_webp):
                    changed_count += 1
    return changed_count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--folders', nargs='*', default=DEFAULT_FOLDERS)
    parser.add_argument('--quality', type=int, default=75)
    parser.add_argument('--webp', action='store_true', help='Also create WebP versions')
    parser.add_argument('--path', default='.', help='Project root')
    args = parser.parse_args()

    project_root = Path(args.path)
    total = 0
    for folder in args.folders:
        folder_path = project_root / folder
        if folder_path.exists():
            changed = walk_and_optimize(folder_path, quality=args.quality, make_webp=args.webp)
            print(f"Optimized {changed} images in {folder}")
            total += changed
        else:
            print(f"Skipping missing folder: {folder}")
    print(f"Total optimized images: {total}")

if __name__ == '__main__':
    main()
