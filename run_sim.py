"""
1. rng      = default_rng(seed)          ← created ONCE
2. world    = World(rng, ...)
3. book     = LimitOrderBook()
4. engine   = Engine()
5. agents   = two or three NoiseTraders, each given
              (engine, book, world, rng, name, rate, noise, max_qty)
6. schedule the first wake-up for each agent
   schedule the world's first step
   engine.run(until=1000)


"""

import os
 
from numpy.random import default_rng
 
from book.book import LimitOrderBook
from sim.world import World
from sim.engine import Engine
from sim.agents import NoiseTrader, InformedTrader, MarketMaker
from plot_run import plot_run
 
 
def run_once(seed, n_noise=2, n_informed=1, mm_config=None, T=1000):
    world_rng, agent_rng = default_rng(seed).spawn(2)
    world = World(world_rng, fair_value=50.0, sigma=0.1, T=T)
    book = LimitOrderBook()
    engine = Engine()
 
    noise = [
        NoiseTrader(engine=engine, book=book, world=world, rng=agent_rng,
                    name=f"noise_{i+1}", rate=1.0, noise=5.0, max_qty=10)
        for i in range(n_noise)
    ]
 
    informed = [
        InformedTrader(engine=engine, book=book, world=world, rng=agent_rng,
                       name=f"informed_{i+1}", rate=1.0, threshold=2, qty=10)
        for i in range(n_informed)
    ]

    mm_defaults = {"rate": 1.0, "half_spread": 2, "qty": 10}
    mm = MarketMaker(engine=engine, book=book, world=world, rng=agent_rng,
                     name="mm", **{**mm_defaults, **(mm_config or {})})
 
    history = []
 
    def world_tick():
        world.step()
        history.append((engine.clock, world.fair_value,
                        book.best_bid(), book.best_ask()))
        engine.schedule(1.0, world_tick)
 
    engine.schedule(0.0, world_tick)
 
    for agent in noise + informed + [mm]:
        engine.schedule(1.0, agent.act)
 
    engine.run(until=T)
 
    return {
        "history": history,
        "trades": book.trades,
        "book": book,
        "world": world,
        "engine": engine,
        "noise": noise,
        "informed": informed,
        "mm": mm,
    }
 
 
if __name__ == "__main__":
    os.makedirs("figures", exist_ok=True)
 
    # r = run_once(seed=0, mm_config={"skew": True}) ---- inventory skew
    r = run_once(seed=0, mm_config={"skew": True, "micro": True}) 
    total = len(r["trades"])
    informed_trades = sum(t.n_trades for t in r["informed"])
    """
    print("final fair value:", r["world"].fair_value)
    print("best bid:", r["book"].best_bid())
    print("best ask:", r["book"].best_ask())
    print("total trades:", total)
    print("informed trades:", informed_trades,
          f"({informed_trades / total:.1%})" if total else "")
 
    plot_run(r["history"],
             [(tr.timestamp, tr.price) for tr in r["trades"]],
             out="figures/run_informed.png")
    a = run_once(seed=0, n_informed=0)
    b = run_once(seed=0, n_informed=3)
    print([h[1] for h in a["history"]] == [h[1] for h in b["history"]])
    """
    mm = r["mm"]
    print("--- market maker ---")
    print("fills:", len(mm.my_fills))
    print("inventory:", mm.inventory)
    print("cash:", round(mm.cash, 2))
    print("mark-to-market:", round(mm.cash + mm.inventory * r["world"].fair_value, 2))
    print("final fair value:", r["world"].fair_value)
    print("best bid:", r["book"].best_bid())
    print("best ask:", r["book"].best_ask())
    print("total trades:", total)
    print("informed trades:", informed_trades,
            f"({informed_trades / total:.1%})" if total else "")
     
    plot_run(r["history"],
                [(tr.timestamp, tr.price) for tr in r["trades"]],
             out="figures/mm_v3_micro.png")