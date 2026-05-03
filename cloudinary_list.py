"""
List all files in your Cloudinary account and print direct download URLs for each file.

Usage:
    python cloudinary_list.py

Set these environment variables before running:
    CLOUDINARY_CLOUD_NAME
    CLOUDINARY_API_KEY
    CLOUDINARY_API_SECRET
"""

import os
import cloudinary
import cloudinary.api


def main():



    cloudinary.config(
        cloud_name="dg6xfou1t",
        api_key="875272749645643",
        api_secret="1KRVTKh6DiluDJB2SIovyFpizd0",
        secure=True,
    )

    next_cursor = None
    all_resources = []
    while True:
        response = cloudinary.api.resources(max_results=500, next_cursor=next_cursor)
        resources = response.get('resources', [])
        all_resources.extend(resources)
        next_cursor = response.get('next_cursor')
        if not next_cursor:
            break

    if not all_resources:
        print("No resources found.")
        return

    print("Download links:")
    for idx, res in enumerate(all_resources, start=1):
        url = res.get('secure_url') or res.get('url')
        print(f"{idx}. {res.get('public_id')}: {url}")

    print("\nDone.")


if __name__ == '__main__':
    main()
