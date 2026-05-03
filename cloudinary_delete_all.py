"""
Delete all resources in your Cloudinary account.

Usage:
    python cloudinary_delete_all.py

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
    all_public_ids = []
    while True:
        response = cloudinary.api.resources(max_results=500, next_cursor=next_cursor)
        resources = response.get('resources', [])
        all_public_ids.extend([res['public_id'] for res in resources])
        next_cursor = response.get('next_cursor')
        if not next_cursor:
            break

    if not all_public_ids:
        print("No resources found to delete.")
        return

    print(f"Found {len(all_public_ids)} resources. Deleting...")
    # Cloudinary API allows deleting up to 1000 at a time
    for i in range(0, len(all_public_ids), 100):
        batch = all_public_ids[i:i+100]
        result = cloudinary.api.delete_resources(batch)
        deleted = result.get('deleted', {})
        print(f"Deleted: {', '.join(deleted.keys())}")

    print("\nAll resources deleted.\n")


if __name__ == '__main__':
    main()
