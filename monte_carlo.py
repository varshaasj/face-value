"""Monte Carlo over the market maker configurations.

One run tells you nothing — you need the distribution, or you can't tell a real
effect from a lucky seed. Every config sees the identical set of worlds, so the
comparison is paired: differences are computed seed by seed, which removes the
between-world variance entirely.
"""

import numpy as np

from run_sim import run_once

CONFIGS = {
    "naive":      {},
    "skew":       {"skew": True},
    "micro":      {"micro": True},
    "skew+micro": {"skew": True, "micro": True},
}

N_SEEDS = 50
BASELINE = "skew"          # compare everything against the current best


def collect(n_seeds=N_SEEDS):
    """mtm[config] = array of mark-to-market, one per seed."""
    mtm = {name: [] for name in CONFIGS}
    inv = {name: [] for name in CONFIGS}
    fills = {name: [] for name in CONFIGS}

    for seed in range(n_seeds):
        for name, cfg in CONFIGS.items():
            r = run_once(seed=seed, mm_config=cfg)
            mm, world = r["mm"], r["world"]
            mtm[name].append(mm.cash + mm.inventory * world.fair_value)
            inv[name].append(mm.inventory)
            fills[name].append(len(mm.my_fills))
        if (seed + 1) % 10 == 0:
            print(f"  ...{seed + 1}/{n_seeds} seeds")

    to_arr = lambda d: {k: np.array(v, dtype=float) for k, v in d.items()}
    return to_arr(mtm), to_arr(inv), to_arr(fills)


def main():
    print(f"running {N_SEEDS} seeds x {len(CONFIGS)} configs...")
    mtm, inv, fills = collect()

    print()
    hdr = (f"{'config':<12} {'mean P&L':>10} {'95% CI':>18} "
           f"{'median':>9} {'mean inv':>9} {'mean fills':>11} {'win%':>6}")
    print(hdr)
    print("-" * len(hdr))

    for name in CONFIGS:
        x = mtm[name]
        se = x.std(ddof=1) / np.sqrt(len(x))
        lo, hi = x.mean() - 1.96 * se, x.mean() + 1.96 * se
        win = 100 * (x > 0).mean()
        print(f"{name:<12} {x.mean():>10.1f} {f'[{lo:.0f}, {hi:.0f}]':>18} "
              f"{np.median(x):>9.1f} {inv[name].mean():>9.1f} "
              f"{fills[name].mean():>11.1f} {win:>5.0f}%")

    print()
    print(f"paired difference vs '{BASELINE}' (same seed, so world variance cancels)")
    print("-" * 62)
    base = mtm[BASELINE]
    for name in CONFIGS:
        if name == BASELINE:
            continue
        d = mtm[name] - base
        se = d.std(ddof=1) / np.sqrt(len(d))
        lo, hi = d.mean() - 1.96 * se, d.mean() + 1.96 * se
        verdict = "better" if lo > 0 else "worse" if hi < 0 else "not distinguishable"
        print(f"{name:<12} {d.mean():>10.1f}   95% CI [{lo:>8.1f}, {hi:>8.1f}]   {verdict}")

    return mtm, inv, fills


if __name__ == "__main__":
    main()