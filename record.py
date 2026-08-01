#!/usr/bin/env python3
"""
Face Value — Kalshi top-of-book recorder.

Polls the markets endpoint once per series (top-of-book comes back in the
list response, so ~366 markets cost 7 requests).

Writes a row ONLY when a market's quote actually changes. Nothing is lost —
the quote at any moment is the last recorded change before it — and it cuts
storage by ~90-95%. Row count now measures activity: quiet markets write
almost nothing, markets moving through an information event write a lot.

Run:  python record.py
Stop: ctrl-C
"""

import sqlite3
import sys
import time
from datetime import datetime, timezone

import requests

# ---------------------------------------------------------------- config

SERIES = [
    "KXRT",                      # Rotten Tomatoes — embargo lift, closes Aug 3
    "KXNETFLIXRANKSHOW",         # Netflix TV ranking — Aug 4
    "KXNETFLIXRANKMOVIE",        # Netflix movie ranking — Aug 4
    "KXMC",                      # Metacritic scores — Aug 4
    "KXYTVIEWSW",                # YouTube daily views — Aug 4
    "KXALBUMDEBUT",              # Billboard album debut — Aug 17
    "KXRANKLISTSONGSPOTGLOBAL",  # Spotify Global #1 — expires Aug 1
]

INTERVAL = 30                    # seconds between sweeps
BASE = "https://external-api.kalshi.com/trade-api/v2"
DB = "books.db"

# ---------------------------------------------------------------- schema

conn = sqlite3.connect(DB)
conn.execute("""
CREATE TABLE IF NOT EXISTS tob (
    captured_at TEXT,
    series      TEXT,
    ticker      TEXT,
    title       TEXT,
    close_time  TEXT,
    yes_bid     REAL,
    yes_ask     REAL,
    bid_size    REAL,
    ask_size    REAL,
    volume      REAL,
    status      TEXT
)""")
conn.execute("CREATE INDEX IF NOT EXISTS ix_tk ON tob(ticker, captured_at)")
conn.execute("CREATE INDEX IF NOT EXISTS ix_ts ON tob(captured_at)")
conn.commit()

# ------------------------------------------------- seed the change cache
# Load each ticker's most recent quote so a restart doesn't re-log
# 366 duplicate rows.

last = {}
for row in conn.execute("""
        SELECT ticker, yes_bid, yes_ask, bid_size, ask_size, volume
        FROM tob
        WHERE rowid IN (SELECT MAX(rowid) FROM tob GROUP BY ticker)"""):
    last[row[0]] = tuple(row[1:])

print(f"recording {len(SERIES)} series every {INTERVAL}s -> {DB}")
print(f"change-only writes · {len(last)} tickers already known")
print("ctrl-C to stop\n")

# ---------------------------------------------------------------- loop

sweeps = 0
try:
    while True:
        now = datetime.now(timezone.utc).isoformat()
        rows = []
        seen = 0

        for s in SERIES:
            try:
                r = requests.get(
                    f"{BASE}/markets",
                    params={"series_ticker": s, "status": "open", "limit": 200},
                    timeout=15,
                )
                r.raise_for_status()

                for m in r.json().get("markets", []):
                    seen += 1
                    tk = m.get("ticker")

                    quote = (
                        m.get("yes_bid_dollars"), m.get("yes_ask_dollars"),
                        m.get("yes_bid_size_fp"), m.get("yes_ask_size_fp"),
                        m.get("volume_fp"),
                    )

                    if last.get(tk) == quote:      # nothing moved — skip
                        continue
                    last[tk] = quote

                    rows.append((
                        now, s, tk, m.get("title"), m.get("close_time"),
                        *quote, m.get("status"),
                    ))

            except Exception as e:
                print(f"  ! {s}: {e}", file=sys.stderr, flush=True)

        if rows:
            conn.executemany(
                "INSERT INTO tob VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows)
            conn.commit()

        sweeps += 1
        total = conn.execute("SELECT COUNT(*) FROM tob").fetchone()[0]
        print(f"{now[:19]}  {seen:>4} seen  {len(rows):>4} changed   "
              f"sweep {sweeps}   {total:,} rows total", flush=True)

        time.sleep(INTERVAL)

except KeyboardInterrupt:
    total = conn.execute("SELECT COUNT(*) FROM tob").fetchone()[0]
    print(f"\nstopped after {sweeps} sweeps · {total:,} rows in {DB}")
finally:
    conn.close()