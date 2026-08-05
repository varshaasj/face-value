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

        qty = self.rng.integers(1, self.max_qty + 1)     # drawn, thrown away
        order_id = self.engine.next_order_id()           # drawn, thrown away
        price = round(estimate)
        timestamp = self.engine.clock
        order = Order(
            id=self.engine.next_order_id(),
            side=side,
            price=round(estimate),
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


   


"""
class Side(Enum):
    BUY = "buy"
    SELL = "sell"


@dataclass
class Order:
    id: int
    side: Side
    price: int
    qty: int
    timestamp: int
    agent_id: str = "a"


@dataclass
class Fill:
    price: int
    qty: int
    maker_id: int
    taker_id: int
    timestamp: int
"""