import os, json, requests
from dotenv import load_dotenv

load_dotenv()
KEY = os.environ["TICKETMASTER_KEY"]

r = requests.get("https://app.ticketmaster.com/discovery/v2/events.json",
    params={"apikey": KEY, "classificationName": "music",
            "city": "Chicago", "size": 1})
ev = r.json()["_embedded"]["events"][0]
print("event:", ev["name"], ev["id"])

d = requests.get(
    f"https://app.ticketmaster.com/discovery/v2/events/{ev['id']}.json",
    params={"apikey": KEY}).json()

print("priceRanges:", d.get("priceRanges"))
print("keys:", sorted(d.keys()))