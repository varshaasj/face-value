from book.order import Order, Side
from book.book import LimitOrderBook


def mk(id, side, price, qty, ts):
    return Order(id=id, side=side, price=price, qty=qty, timestamp=ts)


def test_maker_sets_price():
    b = LimitOrderBook()
    b.add_limit(mk(1, Side.SELL, 95, 10, 1))
    fills = b.add_limit(mk(2, Side.BUY, 100, 10, 2))
    assert len(fills) == 1
    assert fills[0].price == 95
    assert fills[0].qty == 10
    assert b.best_bid() is None and b.best_ask() is None


def test_time_priority():
    b = LimitOrderBook()
    b.add_limit(mk(1, Side.SELL, 95, 5, 1))
    b.add_limit(mk(2, Side.SELL, 95, 5, 2))
    fills = b.add_limit(mk(3, Side.BUY, 95, 5, 3))
    assert fills[0].maker_id == 1
    assert b.best_ask() == 95


def test_partial_fill():
    b = LimitOrderBook()
    b.add_limit(mk(1, Side.SELL, 95, 10, 1))
    fills = b.add_limit(mk(2, Side.BUY, 95, 4, 2))
    assert fills[0].qty == 4
    assert b.depth(Side.SELL, 1) == [(95, 6)]


def test_cancel():
    b = LimitOrderBook()
    b.add_limit(mk(1, Side.SELL, 95, 10, 1))
    assert b.cancel(1) is True
    fills = b.add_limit(mk(2, Side.BUY, 100, 10, 2))
    assert fills == []
    assert b.best_bid() == 100 and b.best_ask() is None


def test_walks_multiple_levels():
    b = LimitOrderBook()
    b.add_limit(mk(1, Side.SELL, 95, 5, 1))
    b.add_limit(mk(2, Side.SELL, 96, 5, 2))
    fills = b.add_limit(mk(3, Side.BUY, 96, 8, 3))
    assert [(f.price, f.qty) for f in fills] == [(95, 5), (96, 3)]
    assert b.depth(Side.SELL, 1) == [(96, 2)]


def test_never_crossed():
    b = LimitOrderBook()
    b.add_limit(mk(1, Side.BUY, 90, 5, 1))
    b.add_limit(mk(2, Side.SELL, 95, 5, 2))
    assert b.best_bid() < b.best_ask()