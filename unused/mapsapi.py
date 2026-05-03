# WARNING: replace 'YOUR_GOOGLE_API_KEY' before running
import re
import requests
from bs4 import BeautifulSoup
import googlemaps
from time import sleep

API_KEY = "AIzaSyAELRe-ZcOBPDlxaPfnXhnhVatrDHbW7-4"
gmaps = googlemaps.Client(key=API_KEY)

def find_resorts_near(location_text, radius_m=10000):
    # Use Text Search or Geocode -> Nearby
    # Example: text_search query "resort near <location>"
    query = f"resort near {location_text}"
    resp = gmaps.places(query=query, type="lodging", language="en")
    return resp.get("results", [])

def get_place_details(place_id):
    # Request only needed fields to reduce cost
    fields = [
        "name",
        "formatted_address",
        "formatted_phone_number",
        "website",
        "geometry",
        "place_id"
    ]
    details = gmaps.place(place_id=place_id, fields=fields)
    return details.get("result", {})

def extract_emails_from_website(url):
    emails = set()
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible)"}
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "lxml")

        # Find mailto links
        for a in soup.select('a[href^="mailto:"]'):
            emails.add(a.get('href').split(':', 1)[1].split('?')[0].strip())

        # Fallback: regex search in page text (may find obfuscated results)
        text = soup.get_text(separator=' ')
        for m in re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text):
            emails.add(m)

    except Exception as e:
        # ignore network/parsing errors
        print("Failed to fetch/parse website:", url, "err:", e)
    return list(emails)

def gather_resort_contacts(location_text, max_results=10):
    resorts = find_resorts_near(location_text)
    contacts = []
    for r in resorts[:max_results]:
        place_id = r.get("place_id")
        details = get_place_details(place_id)
        entry = {
            "name": details.get("name"),
            "address": details.get("formatted_address"),
            "phone": details.get("formatted_phone_number"),
            "website": details.get("website"),
            "place_id": details.get("place_id"),
        }

        # Try to get emails from website if present
        if entry["website"]:
            entry["emails"] = extract_emails_from_website(entry["website"])
            # Be polite with rate limits
            sleep(0.5)
        else:
            entry["emails"] = []

        contacts.append(entry)
    return contacts

# Example usage
if __name__ == "__main__":
    results = gather_resort_contacts("Subic, Zambales, Philippines", max_results=5)
    for r in results:
        print(r)
