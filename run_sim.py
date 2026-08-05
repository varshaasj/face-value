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

from numpy.random import default_rng
from book.book import LimitOrderBook    
from sim.world import World
from sim.engine import Engine
from sim.agents import NoiseTrader
from plot_run import plot_run
import os
os.makedirs("figures", exist_ok=True)

rng = default_rng(0)

world  = World(rng, fair_value=50.0, sigma=0.1, T=1000)
book   = LimitOrderBook()
engine = Engine()

traders = [
    NoiseTrader(engine=engine, book=book, world=world, rng=rng,
                name="noise_1", rate=1.0, noise=5.0, max_qty=10),
    NoiseTrader(engine=engine, book=book, world=world, rng=rng,
                name="noise_2", rate=1.0, noise=5.0, max_qty=10),
]

history = []


def world_tick():
    world.step()
    history.append((engine.clock, world.fair_value,
                    book.best_bid(), book.best_ask()))
    engine.schedule(1.0, world_tick)

engine.schedule(0.0, world_tick)

for t in traders:
    engine.schedule(1.0, t.act)

engine.run(until=1000)

print("final fair value:", world.fair_value)
print("best bid:", book.best_bid())
print("best ask:", book.best_ask())


plot_run(history, [(tr.timestamp, tr.price) for tr in book.trades])