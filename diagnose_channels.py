"""Do informed traders cost the market maker, or teach it? Both — separate them.

The threshold sweep produced an inverted U: P&L per fill was WORST at moderate
informed aggressiveness and nearly harmless at maximum aggressiveness. The
hypothesis is that informed traders act through two opposing channels:

  COST     they take money when they strike
  LEARNING their prints are the most informative on the tape, and the market
           maker's reference price is an EWMA of that tape

At threshold=0 they strike constantly for tiny edges and keep the tape glued to
fair value — cheap bites, enormous pricing service. At threshold=3 they wait for
a real mispricing and don't trade often enough to keep the tape current.

The control: give the market maker a reference price that CANNOT learn from flow
(fair value plus fixed-quality noise, which no agent can influence). If the
learning channel is real, the inverted U should disappear and P&L should decline
monotonically with informed aggressiveness.

This is cheating as a strategy. As a diagnostic it's the whole point of having a
simulator — you can run a control that's physically impossible in a real market.
"""

import os

import numpy as np
import matplotlib.pyplot as plt

from run_sim import run_once

THRESHOLDS = [0, 1, 2, 3, 4, 6, 8, 12]
HALF_SPREAD = 3
N_INFORMED = 3
N_SEEDS = 30

REFERENCES = {
    "ewma (learns from the tape)": {"skew": True, "ewma": True},
    "oracle (cannot learn)":       {"skew": True, "oracle": True},
}


def cell(cfg, threshold, n_informed=N_INFORMED, n_seeds=N_SEEDS):
    pnl, fills, shares = [], [], []
    for seed in range(n_seeds):
        r = run_once(seed=seed, n_informed=n_informed,
                     informed_threshold=threshold,
                     mm_config=dict(cfg, half_spread=HALF_SPREAD))
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
        "mean": pnl.mean(), "lo": pnl.mean() - 1.96 * se, "hi": pnl.mean() + 1.96 * se,
        "fills": mean_fills,
        "per_fill": pnl.mean() / mean_fills if mean_fills else float("nan"),
        "share": float(np.mean(shares)) if shares else 0.0,
    }


def main():
    os.makedirs("figures", exist_ok=True)
    print(f"half_spread={HALF_SPREAD}, {N_INFORMED} informed, {N_SEEDS} seeds\n")

    results = {}
    baselines = {}
    for label, cfg in REFERENCES.items():
        print(f"=== {label} ===")
        baselines[label] = cell(cfg, threshold=0, n_informed=0)
        print(f"  baseline (0 informed): {baselines[label]['per_fill']:>6.2f} c/fill")
        for th in THRESHOLDS:
            results[(label, th)] = cell(cfg, th)
            row = results[(label, th)]
            print(f"  threshold={th:>3}  share={row['share']:>5.1%}  "
                  f"per_fill={row['per_fill']:>7.2f}  fills={row['fills']:>6.1f}")
        print()

    print("=" * 72)
    print("COST OF ADVERSE SELECTION (cents/fill, vs that reference's own "
          "zero-informed baseline)")
    hdr = f"{'threshold':>10} {'share':>8}" + "".join(f"{l.split()[0]:>14}" for l in REFERENCES)
    print(hdr)
    print("-" * len(hdr))
    for th in THRESHOLDS:
        share = results[(list(REFERENCES)[0], th)]["share"]
        cells = "".join(
            f"{results[(l, th)]['per_fill'] - baselines[l]['per_fill']:>14.2f}"
            for l in REFERENCES)
        print(f"{th:>10} {share:>7.1%}{cells}")

    print()
    for label in REFERENCES:
        costs = [results[(label, th)]["per_fill"] - baselines[label]["per_fill"]
                 for th in THRESHOLDS]
        worst = THRESHOLDS[int(np.argmin(costs))]
        shape = ("monotonic — worst at max aggressiveness"
                 if worst == THRESHOLDS[0]
                 else f"inverted U — worst at threshold={worst}, not at 0")
        print(f"{label:<30} {shape}")

    # ---- chart -------------------------------------------------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 5.5))
    colors = {list(REFERENCES)[0]: "#c0392b", list(REFERENCES)[1]: "#2c3e50"}

    for label in REFERENCES:
        xs = [results[(label, th)]["share"] * 100 for th in THRESHOLDS]
        ys = [results[(label, th)]["per_fill"] - baselines[label]["per_fill"]
              for th in THRESHOLDS]
        order = np.argsort(xs)
        ax1.plot(np.array(xs)[order], np.array(ys)[order], "o-", lw=2, ms=5,
                 color=colors[label], label=label)
    ax1.axhline(0, color="#111", lw=1, ls="--")
    ax1.set_xlabel("informed share of flow (%)")
    ax1.set_ylabel("cost vs zero-informed baseline (cents/fill)")
    ax1.set_title("Two channels: informed flow costs, and informs")
    ax1.legend(frameon=False, fontsize=9)
    ax1.grid(alpha=0.15)

    for label in REFERENCES:
        ys = [results[(label, th)]["mean"] for th in THRESHOLDS]
        lo = [results[(label, th)]["lo"] for th in THRESHOLDS]
        hi = [results[(label, th)]["hi"] for th in THRESHOLDS]
        ax2.fill_between(THRESHOLDS, lo, hi, alpha=0.15, color=colors[label])
        ax2.plot(THRESHOLDS, ys, "o-", lw=2, ms=5, color=colors[label], label=label)
    ax2.axhline(0, color="#111", lw=1, ls="--")
    ax2.set_xlabel("informed threshold (cents of edge required) — lower is more aggressive")
    ax2.set_ylabel("mean total P&L")
    ax2.set_title(f"Market maker P&L, half-spread {HALF_SPREAD}¢")
    ax2.legend(frameon=False, fontsize=9)
    ax2.grid(alpha=0.15)

    plt.tight_layout()
    out = "figures/experiment_1c_two_channels.png"
    plt.savefig(out, dpi=140)
    print(f"\nsaved {out}")

    return results, baselines


if __name__ == "__main__":
    main()