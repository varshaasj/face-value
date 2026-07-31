import os, sqlite3, requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()
KEY = os.environ["SEATGEEK_CLIENT_ID"]
CITIES = ["Chicago", "New York", "Los Angeles", "Austin", "Nashville"]

conn = sqlite3.connect("facevalue.db")
conn.execute("""CREATE TABLE IF NOT EXISTS snapshots (
    captured_at TEXT, event_id INTEGER, event_name TEXT, performer TEXT,
    venue TEXT, city TEXT, capacity INTEGER, event_datetime TEXT,
    days_to_event REAL, announce_date TEXT, popularity REAL, score REAL,
    is_open INTEGER, status TEXT)""")

now = datetime.now(timezone.utc)
total = 0

for city in CITIES:
    r = requests.get("https://api.seatgeek.com/2/events", params={
        "client_id": KEY, "taxonomies.name": "concert", "venue.city": city,
        "datetime_utc.gte": now.strftime("%Y-%m-%d"),
        "datetime_utc.lte": (now + timedelta(days=120)).strftime("%Y-%m-%d"),
        "per_page": 100, "sort": "score.desc"}, timeout=30)
    r.raise_for_status()

    rows = []
    for e in r.json()["events"]:
        s = e.get("stats") or {}
        p = e.get("performers") or []
        v = e.get("venue") or {}
        dt = e.get("datetime_utc")
        days = (datetime.fromisoformat(dt).replace(tzinfo=timezone.utc)
                - now).total_seconds() / 86400 if dt else None
        rows.append((now.isoformat(), e["id"], e.get("title"),
                     p[0]["name"] if p else None, v.get("name"), v.get("city"),
                     v.get("capacity"), dt, days, e.get("announce_date"),
                     e.get("popularity"), e.get("score"),
                     1 if e.get("is_open") else 0, e.get("status")))

    conn.executemany("INSERT INTO snapshots VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    conn.commit()
    print(f"{city}: {len(rows)}")
    total += len(rows)

print(f"total {total} | all-time {conn.execute('SELECT COUNT(*) FROM snapshots').fetchone()[0]}")
conn.close()