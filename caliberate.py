"""Stage 5.5 — measure the parameters the simulator should run at.

The simulator's numbers were invented. This measures the real equivalents so
Stage 6 can run it at settings that came from data rather than from me.

Four parameters, and what each maps to:

  sigma       World.sigma      volatility of fair value, in LOG-ODDS per step,
                               since that's the space the walk happens in
  rate        agent rate       how often the book changes — a proxy for order
                               arrival, since change-only writes mean a row IS
                               an event
  half_spread MarketMaker      the spread real market makers actually quote
  qty         agent qty        typical size resting at the touch

The proxy in `rate` is the weakest link and worth being honest about: a quote
update is not an order arrival. Several orders can arrive without moving the
top of book, and one can move it twice. It's a lower bound on activity.
"""

import numpy as np
import pandas as pd

import kalshi

STEPS = 1000          # World runs T=1000 steps over a contract's life
CLIP = (1.0, 99.0)


def logit(p_cents):
    p = np.clip(p_cents, *CLIP) / 100.0
    return np.log(p / (1 - p))


def per_contract(df, min_obs=200):
    """One row per contract: measured volatility, activity, spread, size."""
    out = []
    for tkr, g in df.groupby("ticker", sort=False):
        g = g[g["two_sided"]].sort_values("captured_at")
        if len(g) < min_obs:
            continue

        life_min = (g["captured_at"].iloc[-1]
                    - g["captured_at"].iloc[0]).total_seconds() / 60
        if life_min < 60:
            continue

        z = logit(g["mid"].to_numpy())
        dz = np.diff(z)
        dz = dz[np.isfinite(dz)]
        if dz.size < 50:
            continue

        # total variance accumulated over the observed life, then spread it
        # across the simulator's STEPS steps
        total_var = float(np.sum(dz ** 2))
        sigma_per_step = np.sqrt(total_var / STEPS)

        out.append({
            "ticker": tkr,
            "series": g["series"].iloc[0],
            "obs": len(g),
            "life_hours": life_min / 60,
            "updates_per_min": len(g) / life_min,
            "sigma_per_step": sigma_per_step,
            "median_spread": float(g["spread"].median()),
            "median_touch_size": float(
                np.median(np.minimum(g["bid_size"], g["ask_size"]))),
            "median_mid": float(g["mid"].median()),
        })
    return pd.DataFrame(out)


def main():
    df = kalshi.load()
    pc = per_contract(df)
    print(f"{len(pc)} contracts with enough two-sided history\n")

    def q(col, fmt="{:.3f}"):
        s = pc[col]
        return (f"median {fmt.format(s.median())}   "
                f"p25 {fmt.format(s.quantile(.25))}   "
                f"p75 {fmt.format(s.quantile(.75))}")

    print("MEASURED")
    print(f"  sigma (log-odds per step, T={STEPS})   {q('sigma_per_step')}")
    print(f"  quote updates per minute               {q('updates_per_min', '{:.2f}')}")
    print(f"  median spread (cents)                  {q('median_spread', '{:.1f}')}")
    print(f"  median size at the touch (contracts)   {q('median_touch_size', '{:.0f}')}")
    print(f"  contract life (hours)                  {q('life_hours', '{:.1f}')}")

    print("\nBY SERIES (median sigma per step)")
    by = (pc.groupby("series")
            .agg(n=("ticker", "size"),
                 sigma=("sigma_per_step", "median"),
                 updates=("updates_per_min", "median"),
                 spread=("median_spread", "median"))
            .sort_values("n", ascending=False))
    print(by.to_string())

    sim_sigma = 0.1
    med = pc["sigma_per_step"].median()
    print(f"\nCALIBRATION")
    print(f"  simulator currently runs sigma = {sim_sigma}")
    print(f"  measured median                 = {med:.4f}")
    print(f"  ratio                           = {sim_sigma/med:.1f}x too volatile")
    print(f"  half_spread: simulator 2-4c, real median "
          f"{pc['median_spread'].median()/2:.1f}c half-spread")

    return pc


if __name__ == "__main__":
    main()