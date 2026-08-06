"""Load the recorded Kalshi order books into pandas.

The recorder does change-only writes: a row exists only when something about
the top of book actually moved. So a quote HOLDS from its row until the next
one — the gaps are not missing data, they're stretches where nothing happened.
Treating them as missing would silently drop most of the market's life.

`grid()` resamples onto a regular time index and forward-fills, which is the
correct reading of that encoding and what every downstream analysis needs.
"""

from pathlib import Path

import numpy as np
import pandas as pd

DB = Path(__file__).with_name("books.db")


def load(db=DB, series=None, tickers=None):
    """Everything, as recorded. One row per observed change."""
    import sqlite3

    where, params = [], []
    if series:
        where.append(f"series in ({','.join('?' * len(series))})")
        params += list(series)
    if tickers:
        where.append(f"ticker in ({','.join('?' * len(tickers))})")
        params += list(tickers)
    clause = ("where " + " and ".join(where)) if where else ""

    with sqlite3.connect(db) as conn:
        df = pd.read_sql_query(f"select * from tob {clause}", conn, params=params)

    df["captured_at"] = pd.to_datetime(df["captured_at"], utc=True, format="mixed")
    df["close_time"] = pd.to_datetime(df["close_time"], utc=True, format="mixed")

    # Kalshi quotes in dollars (0.28). Everything in this project is cents.
    for c in ("yes_bid", "yes_ask"):
        df[c] = df[c] * 100

    df = df.sort_values(["ticker", "captured_at"]).reset_index(drop=True)
    return _derive(df)


def _derive(df):
    # Kalshi reports yes_ask = 100 when there is NO ask, and yes_bid = 0 when
    # there is no bid. So a book quoted 99/100 looks like a 1c spread and is
    # actually one-sided. Price alone is not enough — check the size.
    two_sided = ((df["yes_bid"] > 0) & (df["yes_ask"] > 0)
                 & (df["bid_size"] > 0) & (df["ask_size"] > 0))
    df["two_sided"] = two_sided
    df["spread"] = np.where(two_sided, df["yes_ask"] - df["yes_bid"], np.nan)
    df["mid"] = np.where(two_sided, (df["yes_ask"] + df["yes_bid"]) / 2, np.nan)

    # size-weighted toward the thin side — the micro-price from the simulator
    tot = df["bid_size"] + df["ask_size"]
    df["micro"] = np.where(
        two_sided & (tot > 0),
        (df["yes_bid"] * df["ask_size"] + df["yes_ask"] * df["bid_size"]) / tot,
        np.nan)

    # positive = more size on the bid, i.e. buying pressure
    tot = df["bid_size"] + df["ask_size"]
    df["imbalance"] = np.where(tot > 0,
                               (df["bid_size"] - df["ask_size"]) / tot, np.nan)

    df["mins_to_close"] = (
        (df["close_time"] - df["captured_at"]).dt.total_seconds() / 60)
    return df


def grid(df, freq="1min", ticker_col="ticker"):
    """Resample onto a regular index, forward-filling within each contract.

    A quote holds until the next recorded change, so forward-fill is the
    correct reading — NOT interpolation, which would invent prices that never
    existed, and NOT dropna, which would delete every quiet period.
    """
    out = []
    for tkr, g in df.groupby(ticker_col, sort=False):
        g = g.set_index("captured_at").sort_index()
        num = g[["yes_bid", "yes_ask", "bid_size", "ask_size", "volume"]]
        r = num.resample(freq).last().ffill()
        r["ticker"] = tkr
        r["series"] = g["series"].iloc[0]
        r["close_time"] = g["close_time"].iloc[0]
        out.append(r)

    g = pd.concat(out).reset_index().rename(columns={"index": "captured_at"})
    return _derive(g)


def resolved(df, min_obs=20):
    """Contracts whose close_time fell inside the recording window."""
    last = df["captured_at"].max()
    counts = df.groupby("ticker").size()
    keep = df.groupby("ticker")["close_time"].first()
    ok = keep[(keep < last)].index.intersection(counts[counts >= min_obs].index)
    return df[df["ticker"].isin(ok)].copy()


if __name__ == "__main__":
    df = load()
    print(f"{len(df):,} rows, {df.ticker.nunique()} contracts, "
          f"{df.captured_at.min():%Y-%m-%d} to {df.captured_at.max():%Y-%m-%d}")
    r = resolved(df)
    print(f"{r.ticker.nunique()} contracts resolved during recording")
    print(f"median spread {df.spread.median():.1f}c   "
          f"genuinely two-sided {df.two_sided.mean():.1%}")