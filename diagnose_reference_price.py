"""Does the EWMA reference price remove the confound?

The pathology: with the book-mid reference, ZERO informed traders was four
times worse than one, because without informed flow the mid decouples from
fair value and the market maker quotes around a stale number.

If the EWMA fix works, more informed flow should make the market maker worse
(adverse selection), not better (a free reference price).
"""

import numpy as np

from run_sim import run_once

INFORMED = [0, 1, 2, 3]
N_SEEDS = 20
HALF_SPREAD = 4

CONFIGS = {
    "mid  (skew)":       {"skew": True},
    "ewma (skew+ewma)":  {"skew": True, "ewma": True},
}


def run(cfg, n_informed, n_seeds=N_SEEDS):
    pnl, drift = [], []
    for seed in range(n_seeds):
        r = run_once(seed=seed, n_informed=n_informed,
                     mm_config=dict(cfg, half_spread=HALF_SPREAD))
        mm, world = r["mm"], r["world"]
        pnl.append(mm.cash + mm.inventory * world.fair_value)

        # how far the book's mid sat from truth, on average
        gaps = [abs((b + a) / 2 - f)
                for _, f, b, a in r["history"]
                if b is not None and a is not None]
        drift.append(np.mean(gaps) if gaps else np.nan)
    return np.array(pnl, dtype=float), float(np.nanmean(drift))


def main():
    print(f"half_spread={HALF_SPREAD}, {N_SEEDS} seeds per cell\n")

    hdr = f"{'reference':<18} {'informed':>9} {'mean P&L':>10} {'|mid-fair|':>11}"
    print(hdr)
    print("-" * len(hdr))

    results = {}
    for label, cfg in CONFIGS.items():
        for n in INFORMED:
            pnl, drift = run(cfg, n)
            results[(label, n)] = pnl.mean()
            print(f"{label:<18} {n:>9} {pnl.mean():>10.1f} {drift:>11.2f}")
        print()

    print("=" * 56)
    for label in CONFIGS:
        zero = results[(label, 0)]
        three = results[(label, 3)]
        direction = "WORSE with informed flow" if three < zero else "BETTER with informed flow"
        print(f"{label:<18} 0 informed {zero:>9.1f}  ->  3 informed {three:>9.1f}   {direction}")

    print()
    print("Expected if the fix works: 'mid' says BETTER (the confound),")
    print("'ewma' says WORSE (adverse selection, which is what we're measuring).")


if __name__ == "__main__":
    main()