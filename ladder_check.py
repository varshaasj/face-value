"""Stage 5.4 — is the market internally consistent?

KXRT-CLA-65 and KXRT-CLA-70 are thresholds on the same number: a film's Rotten
Tomatoes score. They're nested, so "score >= 65" must be at least as likely as
"score >= 70". That's an arbitrage constraint, not a modelling assumption — if
a lower threshold ever trades below a higher one you can buy the cheap leg,
sell the dear one, and be paid to hold a position that cannot lose.

Three things this has to get right, and each one changes the answer:

  1. TWO-SIDED BY SIZE, not price. Kalshi reports ask=100 when there is no ask,
     so a one-sided book reads as a 1c spread.
  2. STALENESS. Forward-filling without a limit compares a fresh quote on one
     leg against a twelve-hour-old quote on the other. They were never live at
     the same moment.
  3. EXECUTABLE PRICES, not mids. To actually arb you buy the low threshold at
     its ASK and sell the high threshold at its BID. A violation in mid-price
     that's smaller than the two spreads is not money.
"""

import os
import re

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import kalshi

FREQ = "5min"
STALE_LIMIT = 2          # periods; 2 x 5min = quotes must be <=10 min apart
MIN_RUNGS = 4


def ladders(df, min_rungs=MIN_RUNGS):
    out = {}
    for t in df["ticker"].unique():
        m = re.match(r"^(.*)-([0-9]+(?:\.[0-9]+)?)$", t)
        if m:
            out.setdefault(m.group(1), []).append((float(m.group(2)), t))
    return {k: sorted(v) for k, v in out.items() if len(v) >= min_rungs}


def panels(df):
    """bid / ask / sizes on a regular grid, forward-filled but not stale."""
    frames = []
    for tkr, g in df[df["two_sided"]].groupby("ticker", sort=False):
        g = g.set_index("captured_at").sort_index()
        r = (g[["yes_bid", "yes_ask", "bid_size", "ask_size"]]
             .resample(FREQ).last().ffill(limit=STALE_LIMIT))
        r["ticker"] = tkr
        frames.append(r)
    g = pd.concat(frames).reset_index()
    piv = lambda c: g.pivot_table(index="captured_at", columns="ticker",
                                  values=c, aggfunc="last")
    bid, ask = piv("yes_bid"), piv("yes_ask")
    return bid, ask, piv("bid_size"), piv("ask_size"), (bid + ask) / 2


def consistency(df):
    bid, ask, bsz, asz, mid = panels(df)
    tot = mid_viol = exe = 0
    best, where, sizes = 0.0, None, []

    for name, rungs in ladders(df).items():
        cols = [t for _, t in rungs if t in mid.columns]
        for lo, hi in zip(cols, cols[1:]):
            idx = mid[[lo, hi]].dropna().index
            if not len(idx):
                continue
            tot += len(idx)
            mid_viol += int((mid.loc[idx, hi] > mid.loc[idx, lo]).sum())

            edge = bid.loc[idx, hi] - ask.loc[idx, lo]     # executable profit
            hit = edge > 0
            exe += int(hit.sum())
            if hit.any():
                e = edge[hit]
                sizes += np.minimum(asz.loc[e.index, lo],
                                    bsz.loc[e.index, hi]).tolist()
                if e.max() > best:
                    best, k = float(e.max()), e.idxmax()
                    where = (lo, hi, k, ask.loc[k, lo], bid.loc[k, hi],
                             asz.loc[k, lo], bsz.loc[k, hi])

    return {"observations": tot, "mid_violations": mid_viol,
            "executable": exe, "best_edge": best, "where": where,
            "sizes": np.array(sizes)}


def main():
    os.makedirs("figures", exist_ok=True)
    df = kalshi.load()
    lads = ladders(df)
    print(f"{len(lads)} ladders with {MIN_RUNGS}+ rungs\n")

    r = consistency(df)
    n = max(r["observations"], 1)
    print(f"adjacent-pair observations (both quoted within 10 min): {r['observations']:,}")
    print(f"  mid-price monotonicity violations : {r['mid_violations']:>6,} "
          f"({100*r['mid_violations']/n:.2f}%)")
    print(f"  EXECUTABLE arbitrage              : {r['executable']:>6,} "
          f"({100*r['executable']/n:.2f}%)")
    if r["where"]:
        lo, hi, k, a, b, sa, sb = r["where"]
        print(f"\n  best executable edge {r['best_edge']:.1f}c — "
              f"buy {lo} at {a:.0f} (size {sa:,.0f}), "
              f"sell {hi} at {b:.0f} (size {sb:,.0f}), at {k}")
    if len(r["sizes"]):
        print(f"  tradeable size at the touch: median "
              f"{np.median(r['sizes']):,.0f} contracts")

    # ---- chart: one ladder resolving ---------------------------------
    spi = [k for k in lads if k.endswith("SPI")]
    if not spi:
        return r
    name = spi[0]
    rungs = lads[name]
    sub = df[df["ticker"].isin([t for _, t in rungs])]
    g = kalshi.grid(sub[sub["two_sided"]], "30min")
    g = g[g["two_sided"]]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 5.5))
    cmap = plt.get_cmap("viridis")

    keep = [(k, t) for k, t in rungs if 85 <= k <= 93]
    for i, (k, t) in enumerate(keep):
        s = g[g["ticker"] == t].set_index("captured_at")["mid"]
        ax1.plot(s.index, s.values, lw=1.8,
                 color=cmap(i / max(len(keep) - 1, 1)), label=f"≥{k:.0f}")
    ax1.set_ylabel("mid (cents = implied probability)")
    ax1.set_title(f"{name} — the ladder resolving (score landed on 89)")
    ax1.legend(frameon=False, fontsize=8, ncol=2)
    ax1.grid(alpha=.15)
    for lab in ax1.get_xticklabels():
        lab.set_rotation(30); lab.set_ha("right")

    _, _, _, _, mid = panels(sub)
    cols = [t for _, t in rungs if t in mid.columns]
    wide = mid[cols].dropna(thresh=max(len(cols) - 2, 2))
    if not wide.empty:
        times = [wide.index[0], wide.index[len(wide) // 2], wide.index[-1]]
        ks = [k for k, t in rungs if t in cols]
        for j, ts in enumerate(times):
            ax2.plot(ks, wide.loc[ts].values, "o-", lw=1.6, ms=4,
                     color=cmap(j / max(len(times) - 1, 1)),
                     label=f"{ts:%d %b %H:%M}")
        ax2.set_xlabel("score threshold")
        ax2.set_ylabel("implied P(score ≥ threshold), cents")
        ax2.set_title("Implied distribution, as information arrives")
        ax2.legend(frameon=False, fontsize=9)
        ax2.grid(alpha=.15)

    plt.tight_layout()
    out = "figures/kalshi_ladder_consistency.png"
    plt.savefig(out, dpi=140)
    print(f"\nsaved {out}")
    return r


if __name__ == "__main__":
    main()