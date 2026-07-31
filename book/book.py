from collections import deque
from sortedcontainers import SortedDict
from book.order import Order, Side, Fill


class LimitOrderBook:
    def __init__(self):
        self.bids = SortedDict()   # price -> deque[Order], ascending keys
        self.asks = SortedDict()   # price -> deque[Order], ascending keys
        self.orders = {}           # order_id -> Order

    # ---- reads -------------------------------------------------

    def best_bid(self):
        return self.bids.keys()[-1] if self.bids else None    # highest

    def best_ask(self):
        return self.asks.keys()[0] if self.asks else None     # lowest

    def mid(self):
        b, a = self.best_bid(), self.best_ask()
        return (b + a) / 2 if b is not None and a is not None else None

    def depth(self, side, n_levels):
        book = self.bids if side is Side.BUY else self.asks
        prices = list(reversed(book.keys())) if side is Side.BUY else list(book.keys())
        return [(p, sum(o.qty for o in book[p])) for p in prices[:n_levels]]

    # ---- writes ------------------------------------------------

    def _rest(self, order):
        book = self.bids if order.side is Side.BUY else self.asks
        book.setdefault(order.price, deque()).append(order)
        self.orders[order.id] = order

    def add_limit(self, order) -> list:
        fills = []
        # TODO: while order.qty > 0 and it crosses the opposite best price:
        #         take the best opposite price level
        #         fill against its orders oldest-first
        #         fill price is the RESTING order's price
        #         drop exhausted orders, delete the level if empty
        if order.qty > 0:
            self._rest(order)
        return fills

    def cancel(self, order_id) -> bool:
        # TODO: find it, remove from its deque, delete empty level
        return False