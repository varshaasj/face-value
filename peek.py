import os, json, requests
from dotenv import load_dotenv

load_dotenv()
r = requests.get("https://api.seatgeek.com/2/events", params={
    "client_id": os.environ["SEATGEEK_CLIENT_ID"],
    "venue.city": "Chicago",
    "taxonomies.name": "concert",
    "per_page": 1,
})
print(json.dumps(r.json()["events"][0], indent=2))