
import requests

API_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-mnli"
# headers = {"Authorization": "Bearer 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"}
headers = {"Authorization": "Bearer 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"}

def classify(text, labels):
    payload = {"inputs": text, "parameters": {"candidate_labels": labels}}
    response = requests.post(API_URL, headers=headers, json=payload)
    print('Raw Response:', response.text)  # Debugging line
    return response.json()

# result = classify("I went cycling and spent Php500 ", ["Travel", "Finance", "Health"])
result = classify("i bought mercedez car for 8000 dollar", ["Travel", "Finance", "Health", "Luxury"])
import re

def classify_and_extract(text, labels):
    # --- Step 1: classify (dummy example for now) ---
    # Replace this with your Hugging Face / OpenAI classifier call
    classification = "Finance" if "Php" in text or "$" in text else "Other"

    # --- Step 2: extract amount ---
    match = re.search(r'(?:Php|₱|\$)\s?(\d+(?:,\d{3})*(?:\.\d{2})?)', text)
    amount = match.group(0) if match else None

    return {"category": classification, "amount": amount}

# Example
result = classify_and_extract("i bought mercedez car for 8000 dollar", ["Travel", "Finance", "Health", "Luxury"])
print(result)


print(result)
# Sample output:
# {
#   "labels": ["Travel", "Finance", "Health"],
#   "scores": [0.92, 0.05, 0.03],
#   "sequence": "I want to book a flight to Madrid"
# }