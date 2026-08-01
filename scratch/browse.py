import requests, time

BASE = "https://external-api.kalshi.com/trade-api/v2"
now = int(time.time())

out, cursor = [], None
for _ in range(15):
    p = {"limit": 1000, "status": "open",
         "min_close_ts": now, "max_close_ts": now + 30 * 86400}
    if cursor:
        p["cursor"] = cursor
    r = requests.get(f"{BASE}/markets", params=p).json()
    ms = r.get("markets", [])
    out += [m for m in ms if not m["ticker"].startswith("KXMVE")]
    cursor = r.get("cursor")
    if not cursor or not ms:
        break

out.sort(key=lambda m: float(m.get("volume_fp") or 0), reverse=True)
print(f"{len(out)} real markets closing within 30 days\n")

for m in out[:40]:
    v = float(m.get("volume_fp") or 0)
    print(f'{v:>12,.0f}  {m.get("yes_bid_dollars")}/{m.get("yes_ask_dollars")}  '
          f'{m["close_time"][:10]}  {m["ticker"][:30]:<30} {(m.get("title") or "")[:50]}')



from collections import defaultdict

by_series = defaultdict(list)
for m in out:
    by_series[m["ticker"].split("-")[0]].append(m)

rows = []
for s, g in by_series.items():
    g.sort(key=lambda m: float(m.get("volume_fp") or 0), reverse=True)
    tot = sum(float(m.get("volume_fp") or 0) for m in g)
    rows.append((tot, s, len(g), g[0]))

rows.sort(reverse=True, key=lambda r: r[0])
print(f"\n{len(rows)} distinct series\n")
for tot, s, n, m in rows[:50]:
    print(f'{tot:>12,.0f} {n:>4} mkts  {m["close_time"][:10]}  '
          f'{s[:24]:<24} {(m.get("title") or "")[:48]}')



out, cursor = [], None
for i in range(15):
    p = {"limit": 1000, "status": "open",
         "min_close_ts": now, "max_close_ts": now + 30 * 86400}
    if cursor:
        p["cursor"] = cursor
    r = requests.get(f"{BASE}/markets", params=p).json()
    ms = r.get("markets", [])
    cursor = r.get("cursor")
    print(f"page {i}: {len(ms)} markets, next cursor: {bool(cursor)}")
    out += [m for m in ms if not m["ticker"].startswith("KXMVE")]
    if not cursor or not ms:
        break



r = requests.get(f"{BASE}/series", params={"category": "Entertainment"}).json()
print(list(r.keys()))
print(r)