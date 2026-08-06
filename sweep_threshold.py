"""Experiment 1b — the dose-response curve.

Sweeping the NUMBER of informed traders barely moved informed share (24% to
32%), because informed traders only act when there's an edge. The dial that
actually moves toxicity is their THRESHOLD: how big a mispricing they need
before they bother.

threshold=0  -> takes any edge at all, maximally toxic
threshold=12 -> almost never trades, effectively no informed flow

Number of informed traders sets how OFTEN they strike. Threshold sets how far
they can REACH. This sweeps reach.
"""

import os

import numpy as np
import matplotlib.pyplot as plt

from run_sim import run_once

THRESHOLDS = [0, 1, 2, 3, 4, 6, 8, 12]
SPREADS = [2, 3, 4]
N_INFORMED = 3
N_SEEDS = 30
CONFIG = {"skew": True, "ewma": True}


def cell(threshold, half_spread, n_seeds=N_SEEDS):
    pnl, fills, shares = [], [], []
    for seed in range(n_seeds):
        r = run_once(seed=seed, n_informed=N_INFORMED,
                     informed_threshold=threshold,
                     mm_config=dict(CONFIG, half_spread=half_spread))
        mm, world = r["mm"], r["world"]
        pnl.append(mm.cash + mm.inventory * world.fair_value)
        fills.append(len(mm.my_fills))
        total = len(r["trades"])
        if total:
            shares.append(sum(t.n_trades for t in r["informed"]) / total)

    pnl = np.array(pnl, dtype=float)
    mean_fills = float(np.mean(fills))
    se = pnl.std(ddof=1) / np.sqrt(len(pnl))
    return {
        "mean": pnl.mean(),
        "lo": pnl.mean() - 1.96 * se,
        "hi": pnl.mean() + 1.96 * se,
        "fills": mean_fills,
        "per_fill": pnl.mean() / mean_fills if mean_fills else float("nan"),
        "share": float(np.mean(shares)) if shares else 0.0,
    }


def main():
    os.makedirs("figures", exist_ok=True)
    print(f"{len(THRESHOLDS)} thresholds x {len(SPREADS)} spreads x {N_SEEDS} seeds, "
          f"{N_INFORMED} informed traders\n")

    grid = {}
    for th in THRESHOLDS:
        for hs in SPREADS:
            grid[(th, hs)] = cell(th, hs)
        shares = [grid[(th, hs)]["share"] for hs in SPREADS]
        print(f"  threshold={th:>3}  informed share ~{np.mean(shares):>5.1%}")

    print("\n" + "=" * 66)
    print("INFORMED SHARE OF FLOW")
    hdr = f"{'threshold':>10}" + "".join(f"{f'hs={hs}':>10}" for hs in SPREADS)
    print(hdr)
    print("-" * len(hdr))
    for th in THRESHOLDS:
        print(f"{th:>10}" + "".join(f"{grid[(th,hs)]['share']:>9.1%} " for hs in SPREADS))

    print("\nP&L PER FILL (cents)")
    print(hdr)
    print("-" * len(hdr))
    for th in THRESHOLDS:
        print(f"{th:>10}" + "".join(f"{grid[(th,hs)]['per_fill']:>10.2f}" for hs in SPREADS))

    # cost relative to the least-toxic case
    quiet = THRESHOLDS[-1]
    print(f"\nCOST OF ADVERSE SELECTION (cents/fill, vs threshold={quiet})")
    print(hdr)
    print("-" * len(hdr))
    for th in THRESHOLDS[:-1]:
        cells = "".join(
            f"{grid[(th,hs)]['per_fill'] - grid[(quiet,hs)]['per_fill']:>10.2f}"
            for hs in SPREADS)
        print(f"{th:>10}{cells}")

    # ---- chart -------------------------------------------------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 5.5))
    cmap = plt.get_cmap("viridis")

    for i, hs in enumerate(SPREADS):
        xs = [grid[(th, hs)]["share"] * 100 for th in THRESHOLDS]
        ys = [grid[(th, hs)]["per_fill"] for th in THRESHOLDS]
        order = np.argsort(xs)
        ax1.plot(np.array(xs)[order], np.array(ys)[order], "o-", lw=2, ms=5,
                 color=cmap(i / max(len(SPREADS) - 1, 1)),
                 label=f"half-spread {hs}¢")
    ax1.axhline(0, color="#111", lw=1, ls="--")
    ax1.set_xlabel("informed share of flow (%)")
    ax1.set_ylabel("P&L per fill (cents)")
    ax1.set_title("The price of adverse selection")
    ax1.legend(frameon=False, fontsize=9)
    ax1.grid(alpha=0.15)

    for i, hs in enumerate(SPREADS):
        ys = [grid[(th, hs)]["mean"] for th in THRESHOLDS]
        lo = [grid[(th, hs)]["lo"] for th in THRESHOLDS]
        hi = [grid[(th, hs)]["hi"] for th in THRESHOLDS]
        c = cmap(i / max(len(SPREADS) - 1, 1))
        ax2.fill_between(THRESHOLDS, lo, hi, alpha=0.15, color=c)
        ax2.plot(THRESHOLDS, ys, "o-", lw=2, ms=5, color=c,
                 label=f"half-spread {hs}¢")
    ax2.axhline(0, color="#111", lw=1, ls="--")
    ax2.set_xlabel("informed trader threshold (cents of edge required)")
    ax2.set_ylabel("mean total P&L")
    ax2.set_title("Market maker P&L vs how aggressive informed traders are")
    ax2.legend(frameon=False, fontsize=9)
    ax2.grid(alpha=0.15)

    plt.tight_layout()
    out = "figures/experiment_1b_threshold_sweep.png"
    plt.savefig(out, dpi=140)
    print(f"\nsaved {out}")

    return grid


if __name__ == "__main__":
    main()