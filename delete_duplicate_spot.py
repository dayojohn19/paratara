#!/usr/bin/env python3
"""
Script to find and delete duplicate "Beto Cold Spring" tourist spots.
"""
import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webSchedule.settings')
django.setup()

from home.models import TouristSpot

# Find all spots with "Beto Cold Spring" in the name
spots = TouristSpot.objects.filter(name__icontains='Beto Cold Spring')

print(f"\n{'='*60}")
print(f"Found {spots.count()} tourist spot(s) matching 'Beto Cold Spring'")
print(f"{'='*60}\n")

for idx, spot in enumerate(spots, 1):
    print(f"Spot #{idx}:")
    print(f"  ID: {spot.id}")
    print(f"  Name: {spot.name}")
    print(f"  Place: {spot.place.placename}")
    print(f"  Slug: {spot.slug}")
    print(f"  Description: {spot.desc[:100]}..." if spot.desc else "  Description: (empty)")
    print(f"  Coordinates: {spot.coords}")
    print(f"  Visit Count: {spot.tourists.count()}")
    print()

if spots.count() > 1:
    print("\nDuplicate entries found!")
    print("\nWhich one would you like to keep?")
    print("Enter the Spot # to KEEP (the others will be deleted)")
    print("Or enter 'cancel' to exit without deleting")
    
    choice = input("\nYour choice: ").strip().lower()
    
    if choice == 'cancel':
        print("\nCanceled. No changes made.")
    else:
        try:
            keep_idx = int(choice) - 1
            if 0 <= keep_idx < spots.count():
                spots_list = list(spots)
                keep_spot = spots_list[keep_idx]
                
                print(f"\nKeeping: {keep_spot.name} (ID: {keep_spot.id})")
                print("\nDeleting:")
                
                for idx, spot in enumerate(spots_list):
                    if idx != keep_idx:
                        print(f"  - {spot.name} (ID: {spot.id})")
                
                confirm = input("\nConfirm deletion? (yes/no): ").strip().lower()
                
                if confirm == 'yes':
                    deleted_count = 0
                    for idx, spot in enumerate(spots_list):
                        if idx != keep_idx:
                            spot.delete()
                            deleted_count += 1
                    
                    print(f"\n✓ Successfully deleted {deleted_count} duplicate(s)!")
                    print(f"✓ Kept: {keep_spot.name} (ID: {keep_spot.id})")
                else:
                    print("\nCanceled. No changes made.")
            else:
                print(f"\nInvalid choice. Please enter a number between 1 and {spots.count()}")
        except ValueError:
            print("\nInvalid input. Please enter a number or 'cancel'")
elif spots.count() == 1:
    print("Only one entry found. No duplicates to delete.")
else:
    print("No entries found matching 'Beto Cold Spring'.")
