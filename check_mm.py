"""Reconcile the market maker's own accounting against the book's trade tape.

The MM builds inventory and cash from its fill mailbox. This recomputes both
from book.trades independently. If the two disagree, the mailbox is wrong and
every P&L number downstream is wrong with it.
"""

from run_sim import run_once
from book.order import Side

CONFIGS = {
    "naive":      {},
    "skew":       {"skew": True},
    "micro":      {"micro": True},
    "skew+micro": {"skew": True, "micro": True},
}


def recompute(book, mm):
    """Inventory and cash, derived only from the tape and the MM's posted ids."""
    inv = 0
    cash = 0.0
    n = 0
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
    return inv, cash, n


def main():
    print(f"{'config':<12} {'inv(mm)':>8} {'inv(tape)':>10} "
          f"{'cash(mm)':>10} {'cash(tape)':>11} {'fills':>6} {'tape':>5}  ok")
    print("-" * 78)

    all_ok = True
    for name, cfg in CONFIGS.items():
        r = run_once(seed=0, mm_config=cfg)
        mm, book = r["mm"], r["book"]
        inv, cash, n = recompute(book, mm)

        ok = (inv == mm.inventory) and abs(cash - mm.cash) < 1e-9 and n == len(mm.my_fills)
        all_ok = all_ok and ok

        print(f"{name:<12} {mm.inventory:>8} {inv:>10} "
              f"{mm.cash:>10.0f} {cash:>11.0f} "
              f"{len(mm.my_fills):>6} {n:>5}  {'OK' if ok else 'MISMATCH'}")

    print()
    if all_ok:
        print("All four reconcile. The mailbox accounting is correct.")
    else:
        print("MISMATCH — the market maker's P&L numbers are not trustworthy.")


if __name__ == "__main__":
    main()