"""Experiment 1 — the price of adverse selection, in cents per fill.

For each level of informed flow, sweep the market maker's half-spread and
record P&L per fill. Dividing by fills matters: more informed flow means more
trades, so raw P&L confounds "each trade is worse" with "there are more of
them". Cents per fill is what a market maker actually thinks in, and it's
directly comparable to the spread being quoted.

Break-even spread is reported too, but it barely moves with informed count —
it's set by the informed traders' threshold (how far they can reach), not by
how many of them there are.
"""

import os

import numpy as np
import matplotlib.pyplot as plt

from run_sim import run_once
from sweep_spread import sweep, breakeven, MIN_FILLS

INFORMED = [0, 1, 2, 3, 4]
SPREADS = [1, 2, 3, 4, 5, 6, 8, 10, 12, 16]
FOCUS = [2, 3, 4, 5, 6]          # spreads where the MM actually trades
N_SEEDS = 30
CONFIG = {"skew": True, "ewma": True}


def informed_share(n_informed, half_spread=4, n_seeds=10):
    """Measured fraction of all trades an informed trader was part of."""
    if n_informed == 0:
        return 0.0
    shares = []
    for seed in range(n_seeds):
        r = run_once(seed=seed, n_informed=n_informed,
                     mm_config=dict(CONFIG, half_spread=half_spread))
        total = len(r["trades"])
        if total:
            shares.append(sum(t.n_trades for t in r["informed"]) / total)
    return float(np.mean(shares)) if shares else 0.0


def main():
    os.makedirs("figures", exist_ok=True)

    points = []
    for n in INFORMED:
        print(f"\n=== {n} informed trader(s) ===")
        rows = sweep(spreads=SPREADS, n_seeds=N_SEEDS, config=CONFIG, n_informed=n)
        be = breakeven(rows)
        share = informed_share(n)
        points.append({"n": n, "rows": rows, "be": be, "share": share})
        print(f"  informed share {share:.1%}   "
              f"break-even {f'{be:.2f}c' if be else 'none'}")

    by_hs = {r["hs"]: {} for r in points[0]["rows"]}
    for p in points:
        for r in p["rows"]:
            by_hs[r["hs"]][p["n"]] = r

    print("\n" + "=" * 74)
    print("P&L PER FILL  (cents)")
    hdr = f"{'half_spread':>11}" + "".join(f"{f'{n} inf':>10}" for n in INFORMED)
    print(hdr)
    print("-" * len(hdr))
    for hs in SPREADS:
        cells = "".join(f"{by_hs[hs][n]['per_fill']:>10.2f}" for n in INFORMED)
        flag = "" if by_hs[hs][INFORMED[-1]]["fills"] >= MIN_FILLS else "   (abstaining)"
        print(f"{hs:>11}{cells}{flag}")

    print("\nCOST OF ADVERSE SELECTION (cents per fill, vs zero informed flow)")
    hdr2 = f"{'half_spread':>11}" + "".join(f"{f'{n} inf':>10}" for n in INFORMED[1:])
    print(hdr2)
    print("-" * len(hdr2))
    costs = []
    for hs in FOCUS:
        base = by_hs[hs][0]["per_fill"]
        deltas = [by_hs[hs][n]["per_fill"] - base for n in INFORMED[1:]]
        costs.append(deltas[-1])
        print(f"{hs:>11}" + "".join(f"{d:>10.2f}" for d in deltas))

    print(f"\nmean cost at highest informed flow ({points[-1]['share']:.0%} of trades): "
          f"{np.mean(costs):+.2f} cents per fill")

    # ---- chart -------------------------------------------------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 5.5))
    cmap = plt.get_cmap("viridis")
    shares = [p["share"] * 100 for p in points]

    for i, hs in enumerate(FOCUS):
        ys = [by_hs[hs][p["n"]]["per_fill"] for p in points]
        ax1.plot(shares, ys, "o-", lw=2, ms=5,
                 color=cmap(i / max(len(FOCUS) - 1, 1)),
                 label=f"half-spread {hs}¢")
    ax1.axhline(0, color="#111", lw=1, ls="--")
    ax1.set_xlabel("informed share of flow (%)")
    ax1.set_ylabel("P&L per fill (cents)")
    ax1.set_title("The price of adverse selection")
    ax1.legend(frameon=False, fontsize=9)
    ax1.grid(alpha=0.15)

    for i, p in enumerate(points):
        hs = [r["hs"] for r in p["rows"]]
        ax2.plot(hs, [r["mean"] for r in p["rows"]], "o-", lw=1.5, ms=4,
                 color=cmap(i / max(len(points) - 1, 1)),
                 label=f"{p['n']} informed ({p['share']:.0%})")
    ax2.axhline(0, color="#111", lw=1, ls="--")
    ax2.set_xlabel("half-spread (cents)")
    ax2.set_ylabel("mean total P&L")
    ax2.set_title("P&L vs spread, by informed flow")
    ax2.legend(frameon=False, fontsize=9)
    ax2.grid(alpha=0.15)

    plt.tight_layout()
    out = "figures/experiment_1_adverse_selection.png"
    plt.savefig(out, dpi=140)
    print(f"\nsaved {out}")

    return points


if __name__ == "__main__":
    main()