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

        qty = self.rng.integers(1,self.max_qty + 1)
        price = round(estimate)
        timestamp = self.engine.clock
        order_id = self.engine.next_order_id()
        order = Order(
            id=self.engine.next_order_id(),
            side=side,
            price=round(estimate),
            qty=int(self.rng.integers(1, self.max_qty + 1)),
            timestamp=self.engine.clock,
            agent_id=self.name,
        )

        fills = self.book.add_limit(order)
        if fills:                                    # temporary — delete later
            for f in fills:
                print(f"  fill {f.qty} @ {f.price}")

        delay = self.rng.exponential(1 / self.rate)
        self.engine.schedule(delay, self.act)


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