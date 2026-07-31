import requests

r = requests.get("https://external-api.kalshi.com/trade-api/v2/markets",
                 params={"limit": 5, "status": "open"})
print("status:", r.status_code)
print(r.text[:2000])