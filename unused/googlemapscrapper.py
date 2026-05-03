import requests
import time

API_KEY = "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"

def places_text_search(query):
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {
        "query": query,
        "key": API_KEY
    }

    results = []
    while True:
        res = requests.get(url, params=params).json()
        print(f"Fetched {len(res.get('results', []))} results")

        for place in res.get("results", []):
            print(f"Found place: {place.get('name')} at {place.get('formatted_address')}")
            results.append(place)

        # If there is a next page
        if "next_page_token" in res:
            time.sleep(2)  # required delay
            params = {"key": API_KEY, "pagetoken": res["next_page_token"]}
        else:
            break

    return results


def place_details(place_id):
    url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "key": API_KEY,
        "fields": "name,rating,user_ratings_total,formatted_address,formatted_phone_number,website,types,geometry,plus_code"
    }
    return requests.get(url, params=params).json().get("result", {})


def extract_google_maps(query):
    raw_places = places_text_search(query)
    final_data = []

    for place in raw_places:
        place_id = place["place_id"]
        details = place_details(place_id)

        data = {
            "name": details.get("name", ""),
            "rating": details.get("rating", ""),
            "reviews": details.get("user_ratings_total", ""),
            "address": details.get("formatted_address", ""),
            "phone": details.get("formatted_phone_number", ""),
            "website": details.get("website", ""),
            "types": details.get("types", []),
            "plus_code": details.get("plus_code", {}).get("global_code", "")
        }

        final_data.append(data)

    return final_data


# ---- RUN ----
if __name__ == "__main__":
    print("Extracting Google Maps data...")
    data = extract_google_maps("restaurants")
    for d in data:
        print(d)
