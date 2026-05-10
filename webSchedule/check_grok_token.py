import requests
import json

API_KEY = "YOUR_XAI_API_KEY"

url = "https://api.x.ai/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

payload = {
    "model": "grok-4",
    "messages": [
        {
            "role": "user",
            "content": "Hello"
        }
    ]
}

response = requests.post(url, headers=headers, json=payload)

data = response.json()

print(json.dumps(data, indent=2))

# token usage
usage = data.get("usage", {})

print("Prompt tokens:", usage.get("prompt_tokens"))
print("Completion tokens:", usage.get("completion_tokens"))
print("Total tokens:", usage.get("total_tokens"))