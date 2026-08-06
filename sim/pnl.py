"""P&L decomposition.

Total mark-to-market P&L splits exactly into two attributions:

    spread    per fill: how good was this price versus what the contract was
              actually worth at that instant?
    inventory while holding: what did fair value do to me?

These are not estimates. They sum to the mark-to-market computed independently
from cash and terminal inventory, and `reconcile()` asserts it. If they ever
disagree, the accounting is wrong and every chart downstream is a lie.

Sign convention, once, here: a buy is +qty and decreases cash; a sell is -qty
and increases cash.
"""

import numpy as np


def decompose(my_fills, history, final_inventory, final_fair, cash):
    """Split total P&L into spread capture and inventory risk.

    my_fills : [(timestamp, price, signed_qty)] from the market maker
    history  : [(t, fair_value, best_bid, best_ask)] from the run
    """
    ts = np.array([h[0] for h in history], dtype=float)
    fv = np.array([h[1] for h in history], dtype=float)

    def fair_at(t):
        """Fair value in force at time t.

        The world only steps on the tick, so fair value is constant between
        ticks. This is exact, not an approximation.
        """
        return fv[max(int(np.searchsorted(ts, t, side="right")) - 1, 0)]

    # --- spread: edge captured at the moment of each fill ---------------
    spread_pnl = sum(signed * (fair_at(t) - price)
                     for t, price, signed in my_fills)

    # --- inventory: what fair value did to the position we were holding --
    # Inventory has to be sampled on the SAME grid as fair value, so rebuild
    # it from the fills rather than using the market maker's own wake-up
    # samples, which land on a different clock.
    fill_times = np.array([f[0] for f in my_fills], dtype=float)
    fill_qtys = np.array([f[2] for f in my_fills], dtype=float)
    order = np.argsort(fill_times, kind="stable")
    fill_times, fill_qtys = fill_times[order], fill_qtys[order]
    cum = np.concatenate([[0.0], np.cumsum(fill_qtys)])

    # The move from fv[k] to fv[k+1] lands at tick k+1, so the position
    # exposed to it is every fill that happened strictly before ts[k+1].
    # Sampling one tick later loses exactly one tick of drift per fill, and
    # the reconciliation catches it.
    idx = np.searchsorted(fill_times, ts[1:], side="left")
    inv_exposed = cum[idx]

    inventory_pnl = float(np.sum(inv_exposed * np.diff(fv)))

    # --- terminal: the position still open when the walk stops -----------
    last_tick_fair = fv[-1]
    terminal_pnl = final_inventory * (final_fair - last_tick_fair)

    return {
        "spread": float(spread_pnl),
        "inventory": inventory_pnl,
        "terminal": float(terminal_pnl),
        "total": float(spread_pnl + inventory_pnl + terminal_pnl),
        "mark_to_market": float(cash + final_inventory * final_fair),
    }


def decompose_run(result):
    """Convenience wrapper around a run_once() result dict."""
    mm, world = result["mm"], result["world"]
    return decompose(mm.my_fills, result["history"],
                     mm.inventory, world.fair_value, mm.cash)


def reconcile(parts, tol=1e-6):
    """Assert the decomposition sums to the independently computed P&L."""
    gap = parts["total"] - parts["mark_to_market"]
    assert abs(gap) < tol, (
        f"P&L decomposition does not reconcile: "
        f"spread {parts['spread']:.4f} + inventory {parts['inventory']:.4f} "
        f"+ terminal {parts['terminal']:.4f} = {parts['total']:.4f}, "
        f"but cash + inventory x fair = {parts['mark_to_market']:.4f} "
        f"(gap {gap:.6f})")
    return gap