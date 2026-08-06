"""Break-even spread.

Sweep the market maker's half-spread and find where mean P&L crosses zero.
That crossing, in cents, is what the market maker has to charge to survive the
informed flow it faces — the cost of adverse selection, in readable units.

Uses the 'skew' config: lowest P&L variance of the four, so the crossing
resolves with fewer seeds.

Only rows with at least MIN_FILLS fills count. Above that, the market maker
stops quoting competitively and "profit" is just abstention — zero P&L with
almost no variance. Abstaining is profitable and useless.
"""

import os

import numpy as np
import matplotlib.pyplot as plt

from run_sim import run_once

SPREADS = [1, 2, 3, 4, 5, 6, 8, 10, 12, 16]
N_SEEDS = 20
CONFIG = {"skew": True}
MIN_FILLS = 20


def sweep(spreads=SPREADS, n_seeds=N_SEEDS, config=CONFIG, **run_kwargs):
    rows = []
    for hs in spreads:
        pnl, fills, absinv = [], [], []
        for seed in range(n_seeds):
            cfg = dict(config, half_spread=hs)
            r = run_once(seed=seed, mm_config=cfg, **run_kwargs)
            mm, world = r["mm"], r["world"]
            pnl.append(mm.cash + mm.inventory * world.fair_value)
            fills.append(len(mm.my_fills))
            absinv.append(abs(mm.inventory))

        pnl = np.array(pnl, dtype=float)
        mean_fills = float(np.mean(fills))
        se = pnl.std(ddof=1) / np.sqrt(len(pnl))
        rows.append({
            "hs": hs,
            "mean": pnl.mean(),
            "lo": pnl.mean() - 1.96 * se,
            "hi": pnl.mean() + 1.96 * se,
            "median": float(np.median(pnl)),
            "fills": mean_fills,
            "per_fill": pnl.mean() / mean_fills if mean_fills else float("nan"),
            "absinv": float(np.mean(absinv)),
            "win": 100.0 * (pnl > 0).mean(),
        })
        print(f"  half_spread={hs:>3}  mean={pnl.mean():>9.1f}  fills={mean_fills:>6.1f}")
    return rows


def breakeven(rows, min_fills=MIN_FILLS):
    """Half-spread where mean P&L crosses zero, among rows that actually trade.

    Linear interpolation between the last negative and first positive point.
    Returns None if there's no crossing inside the tradeable region.
    """
    live = [r for r in rows if r["fills"] >= min_fills]
    for a, b in zip(live, live[1:]):
        if a["mean"] <= 0 < b["mean"]:
            t = -a["mean"] / (b["mean"] - a["mean"])
            return a["hs"] + t * (b["hs"] - a["hs"])
    return None


def plot(rows, be=None, out="figures/breakeven_spread.png"):
    hs = [r["hs"] for r in rows]
    mean = [r["mean"] for r in rows]

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(9, 7), sharex=True,
        gridspec_kw={"height_ratios": [3, 1]})

    ax1.axhline(0, color="#111", lw=1, ls="--", zorder=1)
    ax1.fill_between(hs, [r["lo"] for r in rows], [r["hi"] for r in rows],
                     alpha=0.2, color="#c0392b", zorder=0, label="95% CI")
    ax1.plot(hs, mean, "o-", color="#c0392b", lw=2, zorder=2, label="mean P&L")

    if be is not None:
        ax1.axvline(be, color="#2c3e50", lw=1.2, ls=":", zorder=3)
        ax1.annotate(f"break-even ≈ {be:.1f}¢",
                     xy=(be, 0), xytext=(be + 0.6, min(mean) * 0.35),
                     color="#2c3e50", fontsize=10)

    ax1.set_ylabel("mark-to-market P&L")
    ax1.legend(frameon=False, loc="lower right")
    ax1.set_title(f"Break-even spread — {N_SEEDS} seeds per point, inventory-skew market maker")

    ax2.plot(hs, [r["fills"] for r in rows], "o-", color="#2c3e50", lw=1.5)
    ax2.axhline(MIN_FILLS, color="#999", lw=1, ls=":")
    ax2.annotate(f"min {MIN_FILLS} fills", xy=(hs[-1], MIN_FILLS),
                 ha="right", va="bottom", color="#999", fontsize=9)
    ax2.set_ylabel("mean fills")
    ax2.set_xlabel("half-spread (cents)")
    ax2.set_ylim(bottom=0)

    plt.tight_layout()
    plt.savefig(out, dpi=140)
    print(f"saved {out}")


def main():
    os.makedirs("figures", exist_ok=True)
    print(f"sweeping {len(SPREADS)} spreads x {N_SEEDS} seeds...")
    rows = sweep()

    hdr = (f"\n{'half_spread':>11} {'mean P&L':>10} {'95% CI':>20} {'median':>9} "
           f"{'fills':>7} {'per fill':>9} {'|inv|':>7} {'win%':>6}  ")
    print(hdr)
    print("-" * (len(hdr) - 1))
    for r in rows:
        flag = "" if r["fills"] >= MIN_FILLS else "  (abstaining)"
        ci = f"[{r['lo']:.0f}, {r['hi']:.0f}]"
        print(f"{r['hs']:>11} {r['mean']:>10.1f} {ci:>20} {r['median']:>9.1f} "
              f"{r['fills']:>7.1f} {r['per_fill']:>9.2f} {r['absinv']:>7.1f} "
              f"{r['win']:>5.0f}%{flag}")

    be = breakeven(rows)
    print()
    if be is None:
        print(f"no zero crossing among rows with >= {MIN_FILLS} fills — "
              f"either widen SPREADS or this flow is unsurvivable as configured")
    else:
        print(f"break-even half-spread ~ {be:.2f} cents "
              f"(full spread ~ {2*be:.1f}), among configurations that actually trade")

    plot(rows, be)
    return rows, be


if __name__ == "__main__":
    main()