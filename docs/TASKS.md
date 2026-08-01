# Tasks

Stage-by-stage task tracking. See `docs/PROJECT.md` for the full roadmap and framing.

## Stage 2 — Simulation harness (current)

- [ ] `sim/world.py` — fair value as a random walk, plus expiry time
- [ ] `sim/engine.py` — event loop: heapq of (timestamp, seq, callback), `schedule()`, `run()`
- [ ] `sim/agents.py` — `NoiseTrader`, reschedules its own next action
- [ ] Run it, print fills, watch the book populate
- [ ] `InformedTrader` — sees `world.fair_value`, only acts when the book is mispriced
- [ ] `test_determinism`, `test_book_stays_sane`, `test_events_in_order`
