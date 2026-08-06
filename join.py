"""Stage 6 — the join.

The simulator's parameters were invented. Stage 5 measured the real ones. This
runs the simulator at the measured settings and asks whether it reproduces what
the Kalshi data actually shows.

Two comparisons:

  BREAK-EVEN SPREAD  At invented parameters the market maker needed ~4.7c of
                     half-spread to survive. Real Kalshi contracts trade at a
                     1.5c median half-spread. If the simulator's requirement
                     falls toward 1.5c once volatility is set to the measured
                     0.058, the gap was a parameter choice, not a modelling
                     error.

  SPREAD WIDENING    Measured: median spread goes 1c when quiet to 21c when the
                     price has moved >10c in 15 minutes. The simulator produced
                     the same effect from invented numbers. Does it still, at
                     measured ones?

A result either way. Agreement means the mechanism is right. Disagreement
names a specific thing the model is missing, which is more useful than a
number that happens to match.
"""

import os

import numpy as np
import matplotlib.pyplot as plt

from run_sim import run_once
from sweep_spread import sweep, breakeven

# ---- measured in Stage 5 (calibrate.py) ------------------------------
MEASURED_SIGMA = 0.058
MEASURED_HALF_SPREAD = 1.5
# measured in Stage 5 (spread_analysis.py), median spread by recent mid move
MEASURED_WIDENING = {"no move": 1.0, "<1c": 2.0, "1-2c": 3.0,
                     "2-5c": 5.0, "5-10c": 9.0, ">10c": 21.0}

INVENTED_SIGMA = 0.10

SPREADS = [1, 2, 3, 4, 5, 6, 8, 10]
N_SEEDS = 30
CONFIG = {"skew": True, "ewma": True}
N_INFORMED = 3


def widening(sigma, half_spread, seeds=20):
    """Simulated spread, bucketed by how far the mid moved in the last 15 steps.

    Mirrors the Kalshi measurement exactly: same buckets, same 'recent move'
    definition, so the two are comparable rather than merely similar.
    """
    import sim.world as world_mod
    original = world_mod.World.__init__

    def patched(self, rng, fair_value=50.0, sigma=sigma, T=1000):
        original(self, rng, fair_value=fair_value, sigma=sigma, T=T)

    world_mod.World.__init__ = patched
    try:
        moves, spreads = [], []
        for seed in range(seeds):
            r = run_once(seed=seed, n_informed=N_INFORMED,
                         mm_config=dict(CONFIG, half_spread=half_spread))
            h = r["history"]
            mid = np.array([(b + a) / 2 if b is not None and a is not None else np.nan
                            for _, _, b, a in h])
            sp = np.array([a - b if b is not None and a is not None else np.nan
                           for _, _, b, a in h])
            mv = np.abs(mid[15:] - mid[:-15])
            moves.append(mv)
            spreads.append(sp[15:])
    finally:
        world_mod.World.__init__ = original

    mv = np.concatenate(moves)
    sp = np.concatenate(spreads)
    ok = np.isfinite(mv) & np.isfinite(sp)
    mv, sp = mv[ok], sp[ok]

    edges = [-.01, .001, 1, 2, 5, 10, 1e9]
    labels = ["no move", "<1c", "1-2c", "2-5c", "5-10c", ">10c"]
    out = {}
    for lab, lo, hi in zip(labels, edges[:-1], edges[1:]):
        m = (mv > lo) & (mv <= hi)
        out[lab] = (float(np.median(sp[m])) if m.sum() else np.nan, int(m.sum()))
    return out


def main():
    os.makedirs("figures", exist_ok=True)

    inv_rows = sweep(spreads=SPREADS, n_seeds=N_SEEDS, config=CONFIG,
                     n_informed=N_INFORMED, sigma=INVENTED_SIGMA)
    mea_rows = sweep(spreads=SPREADS, n_seeds=N_SEEDS, config=CONFIG,
                     n_informed=N_INFORMED, sigma=MEASURED_SIGMA)

    inv_be = breakeven(inv_rows)
    mea_be = breakeven(mea_rows)

    print("\n" + "=" * 62)
    print("BREAK-EVEN HALF-SPREAD")
    print(f"  simulator, invented sigma {INVENTED_SIGMA}   "
          f"{inv_be:.2f}c" if inv_be else "  none")
    print(f"  simulator, measured sigma {MEASURED_SIGMA}   "
          f"{mea_be:.2f}c" if mea_be else "  none")
    print(f"  Kalshi, actually quoted            {MEASURED_HALF_SPREAD:.2f}c")
    if mea_be:
        print(f"  -> residual: simulator asks for "
              f"{mea_be - MEASURED_HALF_SPREAD:+.2f}c more than the market charges")

    print("\nSPREAD WIDENING (median simulated spread by recent mid move)")
    w = widening(MEASURED_SIGMA, half_spread=2)
    print(f"  {'bucket':<10}{'simulated':>11}{'n':>9}   Kalshi")
    for lab, (med, n) in w.items():
        print(f"  {lab:<10}{med:>10.1f}c{n:>9,}   "
              f"{MEASURED_WIDENING.get(lab, float('nan')):.0f}c")

    quiet = w["no move"][0]
    big = w[">10c"][0]
    if np.isfinite(quiet) and quiet and np.isfinite(big):
        print(f"\n  simulated widening {quiet:.1f}c -> {big:.1f}c  ({big/quiet:.1f}x)")
        rq, rb = MEASURED_WIDENING["no move"], MEASURED_WIDENING[">10c"]
        print(f"  measured  widening {rq:.0f}c -> {rb:.0f}c  ({rb/rq:.1f}x)")

    # ---- chart -------------------------------------------------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 5.5))

    for rows, be, lab, c in [(inv_rows, inv_be, f"invented σ={INVENTED_SIGMA}", "#c0392b"),
                             (mea_rows, mea_be, f"measured σ={MEASURED_SIGMA}", "#2c3e50")]:
        hs = [r["hs"] for r in rows]
        ax1.plot(hs, [r["mean"] for r in rows], "o-", lw=2, ms=5, color=c, label=lab)
        if be:
            ax1.axvline(be, color=c, ls=":", lw=1.2)
    ax1.axvline(MEASURED_HALF_SPREAD, color="#27ae60", lw=2, ls="--",
                label=f"Kalshi actual {MEASURED_HALF_SPREAD}¢")
    ax1.axhline(0, color="#111", lw=1, ls="--")
    ax1.set_xlabel("half-spread (cents)")
    ax1.set_ylabel("mean market maker P&L")
    ax1.set_title("Break-even spread: invented vs measured volatility")
    ax1.legend(frameon=False, fontsize=9)
    ax1.grid(alpha=.15)

    labels = list(w)
    x = np.arange(len(labels))
    sim_vals = [w[l][0] for l in labels]
    real_vals = [MEASURED_WIDENING.get(l, np.nan) for l in labels]
    ax2.bar(x - .2, sim_vals, width=.4, color="#2c3e50", label="simulated")
    ax2.bar(x + .2, real_vals, width=.4, color="#27ae60", label="Kalshi (measured)")
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, rotation=45, ha="right")
    ax2.set_ylabel("median spread (cents)")
    ax2.set_xlabel("|mid move| over the previous 15 steps / minutes")
    ax2.set_title("Spread widening: simulated vs measured")
    ax2.legend(frameon=False, fontsize=9)
    ax2.grid(alpha=.15, axis="y")

    plt.tight_layout()
    out = "figures/stage6_join.png"
    plt.savefig(out, dpi=140)
    print(f"\nsaved {out}")


if __name__ == "__main__":
    main()