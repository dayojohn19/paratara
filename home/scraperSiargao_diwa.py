import requests
from bs4 import BeautifulSoup
import csv
import json
from datetime import datetime, timedelta
from openai import OpenAI
from django.conf import settings

# =============================
# CONFIG
# =============================
URL = "https://www.diwasiargao.com/siargao-travel-guide-nightlife-schedule-in-siargao/"
SOURCE = "diwasiargao.com"
OUTPUT_CSV = "siargao_nightlife_events.csv"

SYSTEM_PROMPT = """
You are a data extraction engine.
Return ONLY valid JSON.
Do not include explanations, markdown, or extra text.
"""

# =============================
# OPENAI CLIENT
# =============================
client = OpenAI(api_key=settings.OPENAI_API_KEY)

# =============================
# WEEKDAY → DATE CALCULATION
# =============================
WEEKDAY_MAP = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6
}

def next_weekday(target_weekday):
    today = datetime.today()
    days_ahead = target_weekday - today.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return today + timedelta(days=days_ahead)

# =============================
# SAFE JSON PARSER
# =============================
def safe_json_parse(text):
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        return json.loads(text[start:end])
    except Exception:
        print("❌ JSON parse failed:")
        print(text)
        return None

# =============================
# OPENAI EVENT NORMALIZER
# =============================
def normalize_event(text, weekday):

    user_prompt = f"""
Extract ONE nightlife event and return STRICT JSON
with EXACTLY these keys:

Title
Place
Details
dateN
monthN
yearN
Website
Source

Rules:
- dateN, monthN, yearN must be numbers
-  date infer the NEXT date from today's date occurrence of {weekday} 
- and yearN must be the current year too
- Do NOT invent information
- Website may be empty
- Source must be "diwasiargao.com"

TEXT:
\"\"\"
{text}
\"\"\"
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0
    )

    raw = response.choices[0].message.content.strip()
    event = safe_json_parse(raw)

    if not event:
        raise ValueError("Invalid JSON returned by OpenAI")

    return event

# =============================
# SCRAPE + EXPORT TO CSV
# =============================
def scrape_diwa_to_csv():

    html = requests.get(URL, timeout=15).text
    soup = BeautifulSoup(html, "html.parser")

    container = soup.select_one(
        "body > div > section.elementor-section.elementor-top-section.elementor-element.elementor-element-5aff022f "
        "> div > div.elementor-column.elementor-col-66 > div "
        "> div.elementor-widget-theme-post-content > div"
    )

    if not container:
        raise RuntimeError("Content container not found")

    elements = container.find_all(["p", "ul"])
    current_day = None
    rows = []

    for el in elements:

        # Detect weekday heading
        if el.name == "p" and el.find("b"):
            day_text = el.get_text(strip=True).replace(":", "")
            if day_text in WEEKDAY_MAP:
                current_day = day_text
            continue

        # Process events list
        if el.name == "ul" and current_day:
            for li in el.find_all("li"):
                raw_text = li.get_text(" ", strip=True)

                try:
                    ai_data = normalize_event(raw_text, current_day)

                    rows.append({
                        "Title": ai_data["Title"],
                        "Place": ai_data["Place"],
                        "Details": ai_data["Details"],
                        "dateN": ai_data["dateN"],
                        "monthN": ai_data["monthN"],
                        "yearN": ai_data["yearN"],
                        "Website": ai_data["Website"],
                        "Source": ai_data["Source"],
                    })

                    print("✅ Event added:", ai_data["Title"])

                except Exception as e:
                    print("❌ Failed event:")
                    print(raw_text)
                    print(e)

    # =============================
    # WRITE CSV
    # =============================
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "Title",
                "Place",
                "Details",
                "dateN",
                "monthN",
                "yearN",
                "Website",
                "Source",
            ]
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n🎉 Saved {len(rows)} events to {OUTPUT_CSV}")

# =============================
# RUN
# =============================
if __name__ == "__main__":
    scrape_diwa_to_csv()
