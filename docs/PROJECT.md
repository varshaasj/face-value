# Face Value

### A market in cultural outcomes — and a market maker trying to survive it

---

## Where this came from

I was waiting for a concert resale ticket to drop in price before the show. It went **up**
instead. The reason turned out to be inventory: fewer than a hundred listings left, and
thin supply doesn't crash — it climbs.

That made me want to understand a market where the seller's inventory becomes worth
**exactly zero** the morning after, which is a genuinely nasty position to have to manage.

Ticket price data turned out to be a paid product — every free API has closed. But I'd
already seen the shape of what I needed: I competed in **IMC Prosperity**, their simulated
trading competition, which is a whole invented market world you write algorithms against.
The lesson from that was that to study a trader, you first need a market to put it in.

So I built one.

**Prediction markets** have the same structure I was originally interested in — hard
expiry, binary settlement to zero — plus a real two-sided order book and free data. And
the contracts I'm recording happen to be about Rotten Tomatoes scores, Netflix rankings,
Billboard debuts and Spotify charts.

Which makes this a market in **cultural outcomes**. That's the world.

---

## The question

> **What does adverse selection cost a market maker around a scheduled information
> release — and does a simulation reproduce it?**

Rotten Tomatoes scores publish when a review embargo lifts. Netflix posts its Top 10 on a
schedule. Billboard drops on Tuesdays. **You know when the information arrives**, so you
can record the book going into it.

---

## Two halves, and why both are needed

**The engine** — a limit order book, a matching engine, a simulated world with noise
traders, informed traders, and a market maker. This is where I can see everything: I
invent fair value, so I know exactly when the market maker was wrong, what its inventory
was, and what a different strategy would have earned.

**The data** — a live recording of ~366 real prediction-market contracts, top of book,
change-only writes, running through real resolutions. This is where I can see nothing
except the outside: quotes moving, spreads widening. No identities, no inventory, no truth.

**The join** — measure real volatility, spreads and arrival rates from the recordings,
feed them into the simulator, and ask whether it reproduces what actually happened.

> Simulation alone is a toy with invented numbers.
> Measurement alone is an observation with no mechanism.
> Together it's a claim about *why*, with evidence on both sides.

---

## Who builds each half in the real world

| Component | Built by |
|---|---|
| Order book + matching engine | **Exchanges** — Kalshi, CME, Nasdaq. *Also every trading firm, as an in-memory replica rebuilt from the market data feed.* |
| Market maker agent | **Trading firms** — IMC, Optiver, Jane Street |
| Simulation harness | Trading firms build these internally to test strategies |

---

## Status

**Done**
- `book/` — limit order book, price-time priority, partial fills, multi-level walking, cancel. **6/6 tests passing.**
- `record.py` — Kalshi recorder, 7 series, ~366 contracts, 30s sweeps, change-only writes
- `collect.py` — SeatGeek collector *(dormant: their free API no longer exposes prices)*

**Next:** Stage 2, the simulation harness.

---

## Roadmap

| Stage | What | Effort |
|---|---|---|
| ~~1~~ | ~~Order book + matching engine~~ | ✅ done |
| **2** | **Simulation harness** — world, event loop, noise + informed traders | ~5.5 h |
| 3 | Market maker v1→v4 — naive → inventory skew → risk-scaled → micro-price | ~5.5 h |
| 4 | ⭐ **Measurement** — P&L decomposition, the adverse selection experiment | ~9 h |
| 5 | Kalshi data analysis — spread through resolution, sum-to-$1 check | ~8.5 h |
| 6 | The join — calibrate the sim from measured data | ~4 h |
| 7 | README, charts, limitations | ~4 h |
| 8 | C++ port + latency benchmark — **September** | ~18 h |

**Stages 2–4 alone are a complete, defensible project with a real result.** Everything
after is additive.

---

## The two charts that are the deliverable

1. **Simulated** — spread P&L flat while inventory P&L collapses, as informed flow rises
2. **Measured** — spread widening through a real information event

Plus, if time allows: an animated GIF of the book evolving during a run, in the README.

---

## Design principles

- **Theme the presentation, not the mechanics.** Agents are noise / informed / market
  maker because that's what they are. The flavour lives in the README and the naming.
- **Prices are integers.** Never floats.
- **Seed everything.** If two runs with the same seed diverge, every result is meaningless.
- **The limitations section is not optional.** Top-of-book only, 30-second sampling, no
  trade tape, no latency, no fees, omniscient informed traders, hand-chosen parameters.
  Say all of it plainly — it's what makes the rest credible.