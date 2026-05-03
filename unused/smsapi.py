import requests

API_KEY = "e4107fc879544f5af4d90cb1180b186a"
NUMBER = "09765514253"       # recipient's number
MESSAGE = "Hello from Semaphore API via Python!"



url = "https://api.semaphore.co/api/v4/messages"
payload = {
    "apikey": API_KEY,
    "number": NUMBER,
    "message": MESSAGE
}

try:
    r = requests.post(url, data=payload)
    print("Status:", r.status_code)
    print("Response:", r.text)  # <-- see Semaphore's exact error
    r.raise_for_status()
except requests.exceptions.RequestException as e:
    print("Error:", e)
