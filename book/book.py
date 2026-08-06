from collections import deque
from sortedcontainers import SortedDict
from book.order import Order, Side, Fill


class LimitOrderBook:
    def __init__(self):
        self.bids = SortedDict()   # price -> deque[Order], ascending keys
        self.asks = SortedDict()   # price -> deque[Order], ascending keys
        self.orders = {}           # order_id -> Order
        self.trades = []
        self.fills_by_agent = {}

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
        while order.qty > 0:
            if order.side == Side.SELL:
                if self.best_bid() is None or order.price > self.best_bid():
                    break
                price = self.best_bid()
                book = self.bids
            else:
                if self.best_ask() is None or order.price < self.best_ask():
                    break
                price = self.best_ask()
                book = self.asks

            fill_order = book[price].popleft()
            fill_qty = min(order.qty, fill_order.qty)

            order.qty -= fill_qty
            fill_order.qty -= fill_qty

            fill = Fill(
                price=price,
                qty=fill_qty,
                maker_id=fill_order.id,
                taker_id=order.id,
                timestamp=order.timestamp,
            )
            fills.append(fill)
            self.trades.append(fill)
            for who in (fill_order.agent_id, order.agent_id):
                self.fills_by_agent.setdefault(who, []).append(fill)


            if fill_order.qty > 0:
                book[price].appendleft(fill_order)
            else:
                del self.orders[fill_order.id]
            if not book[price]:
                del book[price]

        if order.qty > 0:
            self._rest(order)
        return fills

    def cancel(self, order_id) -> bool:
        # TODO: find it, remove from its deque, delete empty level
        if order_id not in self.orders:
            return False
        deletedOrder = self.orders[order_id]
        deletedPrice = deletedOrder.price
        if deletedOrder.side == Side.SELL:
            self.asks[deletedPrice].remove(deletedOrder)
            if not self.asks[deletedPrice]:
                del self.asks[deletedPrice]
        else:
            self.bids[deletedPrice].remove(deletedOrder)
            if not self.bids[deletedPrice]:
                del self.bids[deletedPrice]
        del self.orders[order_id]
        return True