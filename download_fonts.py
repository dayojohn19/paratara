#!/usr/bin/env python3
"""
download_fonts.py
-----------------
Downloads a curated set of Google Fonts (TTF) that work great for
word-art titles, and stores them under:

    garden/assets/fonts/<FamilyName>/<FamilyName>-<Style>.ttf

Examples of the output:
    garden/assets/fonts/Anton/Anton-Regular.ttf
    garden/assets/fonts/Oswald/Oswald-Regular.ttf
    garden/assets/fonts/Oswald/Oswald-Bold.ttf

Usage:
    pip install requests
    python download_fonts.py
"""

import os
import re
import sys

try:
    import requests
except ImportError:
    print("This script needs the 'requests' package.")
    print("Install it with:  pip install requests")
    sys.exit(1)


# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
FONT_DIR = os.path.join("garden", "assets", "fonts")

# (family_name, [weights])
FONTS = [
    # ---- Display / Bold ---------------------------------------------------
    ("Anton",              [400]),
    ("Archivo Black",      [400]),
    ("Bebas Neue",         [400]),
    ("Righteous",          [400]),
    ("Audiowide",          [400]),
    ("Monoton",            [400]),

    # ---- Script / Elegant -------------------------------------------------
    ("Great Vibes",        [400]),
    ("Pacifico",           [400]),
    ("Lobster",            [400]),
    ("Dancing Script",     [400, 700]),
    ("Sacramento",         [400]),

    # ---- Handwritten / Marker --------------------------------------------
    ("Permanent Marker",   [400]),
    ("Shadows Into Light", [400]),
    ("Caveat",             [400, 700]),
    ("Rock Salt",          [400]),

    # ---- Rounded / Playful ------------------------------------------------
    ("Bubblegum Sans",     [400]),
    ("Fredoka One",        [400]),   # if this 404s, swap for ("Fredoka", [500, 600, 700])
    ("Baloo 2",            [400, 700]),
    ("Comfortaa",          [400, 700]),

    # ---- Condensed / Retro -----------------------------------------------
    ("Oswald",             [400, 700]),
    ("Fjalla One",         [400]),
    ("Staatliches",        [400]),

    # ---- Serif / Classic --------------------------------------------------
    ("Playfair Display",   [400, 700]),
    ("Cinzel",             [400, 700]),
    ("Abril Fatface",      [400]),
]

# This User-Agent reliably returns TTF URLs from Google Fonts.
# (Safari 3.1 on an old iPhone)
UA = (
    "Safari 3.1 Mozilla/5.0 (Macintosh; U; PPC Mac OS X 10_5_2; en-gb) "
    "AppleWebKit/526+ (KHTML, like Gecko) Version/3.1 iPhone"
)

WEIGHT_NAMES = {
    "100": "Thin",
    "200": "ExtraLight",
    "300": "Light",
    "400": "Regular",
    "500": "Medium",
    "600": "SemiBold",
    "700": "Bold",
    "800": "ExtraBold",
    "900": "Black",
}


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------
def slugify(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "", name)


def css_url_for(family: str, weights) -> str:
    fam = family.replace(" ", "+")
    if weights == [400]:
        return f"https://fonts.googleapis.com/css2?family={fam}&display=swap"
    w = ";".join(str(x) for x in weights)
    return f"https://fonts.googleapis.com/css2?family={fam}:wght@{w}&display=swap"


def parse_css(css: str):
    """
    Parse a Google Fonts CSS2 response into a list of:
        {"subset": "...", "family": "...", "style": "...",
         "weight": "400", "url": "https://...ttf"}
    Handles both the comment-subset format and a flat list of @font-face rules.
    """
    faces = []

    # First, try to split by subset comments (/* latin */ etc.)
    parts = re.split(r"/\*\s*([^*]+?)\s*\*/", css)
    if len(parts) > 1:
        # Comment-based parsing
        for i in range(1, len(parts), 2):
            subset = parts[i].strip().lower()
            block = parts[i + 1] if i + 1 < len(parts) else ""
            for m in re.finditer(r"@font-face\s*\{([^}]+)\}", block, flags=re.DOTALL):
                body = m.group(1)
                fam_m = re.search(r"font-family\s*:\s*['\"]([^'\"]+)['\"]", body)
                sty_m = re.search(r"font-style\s*:\s*([A-Za-z]+)", body)
                wgt_m = re.search(r"font-weight\s*:\s*(\d+)", body)
                url_m = re.search(r"url\(\s*['\"]?(https?://[^)'\"]+?)['\"]?\s*\)", body)

                if fam_m and url_m:
                    faces.append({
                        "subset": subset,
                        "family": fam_m.group(1),
                        "style":  sty_m.group(1) if sty_m else "normal",
                        "weight": wgt_m.group(1) if wgt_m else "400",
                        "url":    url_m.group(1),
                    })
    else:
        # Flat parsing (no subset comments)
        for m in re.finditer(r"@font-face\s*\{([^}]+)\}", css, flags=re.DOTALL):
            body = m.group(1)
            fam_m = re.search(r"font-family\s*:\s*['\"]([^'\"]+)['\"]", body)
            sty_m = re.search(r"font-style\s*:\s*([A-Za-z]+)", body)
            wgt_m = re.search(r"font-weight\s*:\s*(\d+)", body)
            url_m = re.search(r"url\(\s*['\"]?(https?://[^)'\"]+?)['\"]?\s*\)", body)

            if fam_m and url_m:
                faces.append({
                    "subset": "latin",  # assume latin
                    "family": fam_m.group(1),
                    "style":  sty_m.group(1) if sty_m else "normal",
                    "weight": wgt_m.group(1) if wgt_m else "400",
                    "url":    url_m.group(1),
                })

    return faces


# ---------------------------------------------------------------------------
# DOWNLOAD
# ---------------------------------------------------------------------------
def download_family(family: str, weights):
    folder = os.path.join(FONT_DIR, slugify(family))
    os.makedirs(folder, exist_ok=True)

    css_url = css_url_for(family, weights)
    print(f"\n=== {family}   (weights: {weights})")
    print(f"    {css_url}")

    try:
        r = requests.get(css_url, headers={"User-Agent": UA}, timeout=30)
        r.raise_for_status()
    except Exception as e:
        print(f"    !! could not fetch CSS: {e}")
        return []

    faces = parse_css(r.text)
    if not faces:
        print("    !! no @font-face rules parsed (family name may be wrong).")
        # Debug: show a snippet of the CSS
        print("    --- CSS response snippet ---")
        print(r.text[:500])
        print("    ----------------------------")
        return []

    # Prefer latin subset, but fall back to whatever the API gave us
    latin = [f for f in faces if f["subset"] == "latin"] or faces

    # Last entry per (style, weight) wins — that's usually the latin one
    chosen = {}
    for face in latin:
        chosen[(face["style"], face["weight"])] = face["url"]

    saved = []
    for (style, weight), ttf_url in chosen.items():
        if not ttf_url.lower().endswith(".ttf"):
            print(f"    !! skipping non-TTF URL: {ttf_url}")
            continue

        style_name = WEIGHT_NAMES.get(weight, f"Weight{weight}")
        if style == "italic":
            style_name = "Italic" if style_name == "Regular" else f"{style_name}Italic"

        filename = f"{slugify(family)}-{style_name}.ttf"
        out_path = os.path.join(folder, filename)

        try:
            fr = requests.get(ttf_url, headers={"User-Agent": UA}, timeout=60)
            fr.raise_for_status()
            with open(out_path, "wb") as fh:
                fh.write(fr.content)
            kb = len(fr.content) / 1024
            print(f"    \u2713 {filename}   ({kb:.1f} KB)")
            saved.append(out_path)
        except Exception as e:
            print(f"    !! failed to download {ttf_url}: {e}")

    return saved


def main():
    os.makedirs(FONT_DIR, exist_ok=True)
    print(f"Fonts will be saved under: {os.path.abspath(FONT_DIR)}")

    all_saved = []
    for family, weights in FONTS:
        all_saved.extend(download_family(family, weights))

    print("\n" + "=" * 60)
    print(f"Done. Downloaded {len(all_saved)} font file(s).")
    print("=" * 60)

    if all_saved:
        print("\nPaths (copy-paste straight into wordart3.py):")
        for p in all_saved:
            print("  " + p.replace(os.sep, "/"))


if __name__ == "__main__":
    main()