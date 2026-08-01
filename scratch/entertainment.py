import requests
BASE = "https://external-api.kalshi.com/trade-api/v2"

series = requests.get(f"{BASE}/series",
                      params={"category": "Entertainment"}).json()["series"]
series.sort(key=lambda s: s.get("last_updated_ts") or "", reverse=True)

out = []
for i, s in enumerate(series[:250]):
    r = requests.get(f"{BASE}/markets", params={
        "series_ticker": s["ticker"], "status": "open", "limit": 100}).json()
    ms = [m for m in r.get("markets", []) if float(m.get("volume_fp") or 0) > 0]
    if ms:
        tot = sum(float(m.get("volume_fp") or 0) for m in ms)
        out.append((tot, s["ticker"], s["title"], len(ms), ms[0]["close_time"][:10]))
        print(f'   found {s["ticker"]} — {len(ms)} markets', flush=True)
    if i % 25 == 0:
        print(f"...{i}/250", flush=True)

out.sort(reverse=True)
print(f"\n{len(out)} live series\n")
for tot, tk, ti, n, ct in out:
    print(f'{tot:>10,.0f} {n:>3} mkts  closes {ct}  {tk[:26]:<26} {ti[:40]}')