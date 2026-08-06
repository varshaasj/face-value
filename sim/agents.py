from book.order import Order, Side
class NoiseTrader:
    def __init__(self, name, engine, book, world, rng,
                 rate=1.0, noise=5.0, max_qty=10):
        self.book = book
        self.rng = rng
        self.world = world
        self.noise = noise
        self.engine = engine
        self.name = name
        self.max_qty = max_qty
        self.rate = rate

    def act(self):
        """Wake up, form an estimate, submit an order,
        schedule the next wake-up."""
        estimate = self.world.fair_value + self.rng.normal()*self.noise
        if self.rng.random() < 0.5:
            side = Side.SELL
        else:
            side = Side.BUY
        price = max(1, min(99, round(estimate)))
        order = Order(
            id=self.engine.next_order_id(),
            side=side,
            price=price,
            qty=int(self.rng.integers(1, self.max_qty + 1)),
            timestamp=self.engine.clock,
            agent_id=self.name,
        )
        self.book.add_limit(order)

        delay = self.rng.exponential(1 / self.rate)
        self.engine.schedule(delay, self.act)

class InformedTrader:
    def __init__(self, name, engine, book, world, rng,
                     rate=1.0, threshold=2, qty=10):
            self.book = book
            self.rng = rng
            self.world = world
            self.threshold = threshold
            self.engine = engine
            self.name = name
            self.qty = qty
            self.rate = rate
            self.n_trades = 0

    def act(self):
           """Wake up, form an estimate, submit an order,
           schedule the next wake-up."""

           fair_value = self.world.fair_value
           best_bid = self.book.best_bid()
           best_ask = self.book.best_ask()
           side = None
           price = None

                
           if best_ask is not None and fair_value - best_ask > self.threshold:
                side = Side.BUY
                price = best_ask
           elif best_bid is not None and best_bid - fair_value > self.threshold:
                side = Side.SELL
                price = best_bid
           delay = self.rng.exponential(1 / self.rate)
           self.engine.schedule(delay, self.act) 

           if side is None:
                return

           order = Order(
               id=self.engine.next_order_id(),
               side=side,
               price=price,
               qty=self.qty,
               timestamp=self.engine.clock,
               agent_id=self.name,
           )
           fills = self.book.add_limit(order)
           self.n_trades += len(fills)

class MarketMaker:
     def __init__(self, name, engine, book, world, rng, rate=1.0,
                 half_spread=2, qty=10, gamma=0.05, alpha=0.1, ref_noise=2.0,
                 skew=False, risk_spread=False, micro=False, ewma=False,
                 oracle=False):
        if risk_spread:
            raise NotImplementedError("risk_spread is not built yet")

        self.book = book
        self.rng = rng
        self.world = world
        self.half_spread = half_spread
        self.skew = skew
        self.risk_spread = risk_spread
        self.micro = micro
        self.ewma = ewma
        self.engine = engine
        self.name = name
        self.qty = qty
        self.rate = rate
        self.gamma = gamma
        self.alpha = alpha
        self.n_trades = 0
        self.inventory = 0
        self.cash = 0.0
        self.my_fills = []
        self.quotes = {}
        self.posted = {}
        self.inventory_history = []
        self.ref_estimate = None     # EWMA of trade prices
        self.trade_cursor = 0        # how far into book.trades we've read
        self.ref_noise = ref_noise
        self.oracle = oracle


     def _consume_tape(self):
        """Update the EWMA from every trade printed since the last wake-up.

        The tape is public — anyone can see prices and sizes, just not who
        traded. Unlike the resting book, it only contains prices someone was
        willing to cross at, so it doesn't fossilise the way stale quotes do.
        """
        tape = self.book.trades
        while self.trade_cursor < len(tape):
            px = float(tape[self.trade_cursor].price)
            if self.ref_estimate is None:
                self.ref_estimate = px
            else:
                self.ref_estimate += self.alpha * (px - self.ref_estimate)
            self.trade_cursor += 1

     def _reschedule(self):
        delay = self.rng.exponential(1 / self.rate)
        self.engine.schedule(delay, self.act)
        self.inventory_history.append((self.engine.clock, self.inventory))

     def act(self):
        inbox = self.book.fills_by_agent.get(self.name, [])
        for f in inbox:
            if f.maker_id in self.quotes:
                my_side = self.quotes[f.maker_id]
            elif f.taker_id in self.quotes:
                my_side = self.quotes[f.taker_id]
            else:
                continue

            signed = f.qty if my_side is Side.BUY else -f.qty
            self.inventory += signed
            self.n_trades += 1
            self.cash -= signed * f.price
            self.my_fills.append((f.timestamp, f.price, signed))
        inbox.clear()

        self._consume_tape()

        for oid in list(self.quotes):
            self.book.cancel(oid)
        self.quotes.clear()

        bid = self.book.best_bid()
        ask = self.book.best_ask()

        if self.oracle:
            ref = self.world.fair_value + self.rng.normal() * self.ref_noise
        elif self.ewma and self.ref_estimate is not None:
            ref = self.ref_estimate
        elif bid is not None and ask is not None:
            if self.micro:
                bid_sz = self.book.depth(Side.BUY, 1)[0][1]
                ask_sz = self.book.depth(Side.SELL, 1)[0][1]
                total = bid_sz + ask_sz
                ref = ((bid * ask_sz + ask * bid_sz) / total
                       if total else (bid + ask) / 2)
            else:
                ref = (bid + ask) / 2
        else:
            ref = self.world.fair_value

        if self.skew:
            frac_remaining = self.world.time_remaining(self.engine.clock) / self.world.T
            ref = ref - self.inventory * self.gamma * frac_remaining

        hs = self.half_spread
        bid_price = max(1, min(99, round(ref - hs)))
        ask_price = max(1, min(99, round(ref + hs)))

        # Pinned against the contract's boundary — no two-sided market to make.
        if bid_price >= ask_price:
            self._reschedule()
            return

        for side, px in ((Side.BUY, bid_price), (Side.SELL, ask_price)):
            order = Order(
                id=self.engine.next_order_id(),
                side=side,
                price=px,
                qty=self.qty,
                timestamp=self.engine.clock,
                agent_id=self.name,
            )
            self.quotes[order.id] = side
            self.posted[order.id] = side
            self.book.add_limit(order)

        self._reschedule()