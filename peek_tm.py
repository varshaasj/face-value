import os, json, requests
from dotenv import load_dotenv

load_dotenv()
r = requests.get("https://app.ticketmaster.com/discovery/v2/events.json", params={
    "apikey": os.environ["TICKETMASTER_KEY"],
    "classificationName": "music",
    "city": "Chicago",
    "size": 5,
})
for e in r.json()["_embedded"]["events"]:
    print(e["name"], "|", e.get("dates", {}).get("start", {}).get("localDate"))
    print("   priceRanges:", e.get("priceRanges"))