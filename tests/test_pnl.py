# Add to tests/test_sim.py
from run_sim import run_once
from sim.pnl import decompose_run, reconcile


def test_pnl_decomposition_reconciles():
    """Spread + inventory + terminal must equal cash + inventory x fair value.

    Two completely independent computations of the same number. If they
    disagree the accounting is wrong and every chart is a lie.
    """
    for seed in range(5):
        for cfg in ({}, {"skew": True}, {"skew": True, "ewma": True}):
            r = run_once(seed=seed, n_informed=3, mm_config=dict(cfg, half_spread=3))
            reconcile(decompose_run(r))


def test_mm_accounting_matches_the_tape():
    """The market maker's own inventory and cash must match what the book did."""
    from book.order import Side

    r = run_once(seed=0, n_informed=3, mm_config={"skew": True, "half_spread": 3})
    mm, book = r["mm"], r["book"]

    inv, cash, n = 0, 0.0, 0
    for t in book.trades:
        if t.maker_id in mm.posted:
            side = mm.posted[t.maker_id]
        elif t.taker_id in mm.posted:
            side = mm.posted[t.taker_id]
        else:
            continue
        signed = t.qty if side is Side.BUY else -t.qty
        inv += signed
        cash -= signed * t.price
        n += 1

    assert inv == mm.inventory
    assert abs(cash - mm.cash) < 1e-9
    assert n == len(mm.my_fills)