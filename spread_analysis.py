"""Stage 5.3 — does the spread widen when information arrives?

Two questions, both about the same thing from different angles:

  1. Does the spread widen as a contract approaches its scheduled resolution?
  2. Does the spread widen when the price is actually MOVING — i.e. when
     information is arriving rather than merely when the clock is running out?

The second is the one the simulator makes a claim about. Adverse selection is
about being picked off by someone who knows something, and what identifies
"someone knew something" in data you can only see from outside is that the
price moved.

Only genuinely two-sided quotes count. Kalshi reports ask=100 with no ask and
bid=0 with no bid, so price alone reads a one-sided book as a 1c spread.
"""

import os

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import kalshi

FREQ = "5min"
BUCKETS = [0, 15, 30, 60, 120, 240, 480, 960, 1920, 1e9]
LABELS = ["0-15m", "15-30m", "30-60m", "1-2h", "2-4h", "4-8h", "8-16h",
          "16-32h", ">32h"]


def prepare(min_obs=50):
    df = kalshi.load()
    df = kalshi.resolved(df, min_obs=min_obs)
    g = kalshi.grid(df, FREQ)
    g = g[g["mins_to_close"].between(0, 4320)]          # last 3 days only

    # absolute mid move over the previous 15 minutes, per contract
    g = g.sort_values(["ticker", "captured_at"])
    steps = max(int(pd.Timedelta("15min") / pd.Timedelta(FREQ)), 1)
    g["move"] = (g.groupby("ticker")["mid"]
                  .diff(steps).abs())
    return g


def summarise(g):
    live = g[g["two_sided"] & g["spread"].notna()].copy()
    live["bucket"] = pd.cut(live["mins_to_close"], BUCKETS, labels=LABELS,
                            right=False)

    by_time = (live.groupby("bucket", observed=True)
                   .agg(median_spread=("spread", "median"),
                        mean_spread=("spread", "mean"),
                        n=("spread", "size"),
                        contracts=("ticker", "nunique")))

    moved = live[live["move"].notna()].copy()
    moved["move_bucket"] = pd.cut(
        moved["move"], [-.01, .001, 1, 2, 5, 10, 1e9],
        labels=["no move", "<1c", "1-2c", "2-5c", "5-10c", ">10c"])
    by_move = (moved.groupby("move_bucket", observed=True)
                    .agg(median_spread=("spread", "median"),
                         mean_spread=("spread", "mean"),
                         n=("spread", "size")))

    # how often is the book one-sided, by time bucket — the other way a
    # market maker withdraws
    allq = g.copy()
    allq["bucket"] = pd.cut(allq["mins_to_close"], BUCKETS, labels=LABELS,
                            right=False)
    one_sided = (allq.groupby("bucket", observed=True)["two_sided"]
                     .apply(lambda s: 1 - s.mean()))

    return by_time, by_move, one_sided


def main():
    os.makedirs("figures", exist_ok=True)
    g = prepare()
    print(f"{g.ticker.nunique()} resolved contracts, {len(g):,} gridded observations\n")

    by_time, by_move, one_sided = summarise(g)

    print("SPREAD BY TIME TO RESOLUTION")
    out = by_time.copy()
    out["one_sided_%"] = (one_sided * 100).round(1)
    print(out.to_string())

    print("\nSPREAD BY SIZE OF THE LAST 15 MINUTES' PRICE MOVE")
    print(by_move.to_string())

    base = by_move.loc["no move", "median_spread"] if "no move" in by_move.index else np.nan
    big = by_move["median_spread"].iloc[-1]
    if np.isfinite(base) and base:
        print(f"\nquiet -> biggest-move bucket: {base:.1f}c -> {big:.1f}c "
              f"({big/base:.1f}x)")

    # ---- chart -------------------------------------------------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 5.5))

    x = np.arange(len(by_time))
    ax1.bar(x, by_time["median_spread"], color="#c0392b", alpha=.85)
    ax1.set_xticks(x)
    ax1.set_xticklabels(by_time.index, rotation=45, ha="right")
    ax1.set_ylabel("median spread (cents)")
    ax1.set_xlabel("time to scheduled resolution")
    ax1.set_title("Spread into resolution")
    ax1.invert_xaxis()

    ax1b = ax1.twinx()
    ax1b.plot(x, one_sided.reindex(by_time.index).values * 100, "o--",
              color="#2c3e50", lw=1.5, ms=4)
    ax1b.set_ylabel("% of quotes one-sided", color="#2c3e50")
    ax1b.set_ylim(bottom=0)

    x2 = np.arange(len(by_move))
    ax2.bar(x2, by_move["median_spread"], color="#2c3e50", alpha=.85)
    ax2.set_xticks(x2)
    ax2.set_xticklabels(by_move.index, rotation=45, ha="right")
    ax2.set_ylabel("median spread (cents)")
    ax2.set_xlabel("|mid move| over the previous 15 minutes")
    ax2.set_title("Spread when the price is moving")

    plt.tight_layout()
    out_path = "figures/kalshi_spread_through_resolution.png"
    plt.savefig(out_path, dpi=140)
    print(f"\nsaved {out_path}")
    return by_time, by_move, one_sided


if __name__ == "__main__":
    main()