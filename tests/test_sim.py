from run_sim import run_once


def test_determinism():
    a = run_once(seed=0)
    b = run_once(seed=0)
    assert len(a["trades"]) == len(b["trades"])
    for x, y in zip(a["trades"], b["trades"]):
        assert (x.price, x.qty, x.timestamp) == (y.price, y.qty, y.timestamp)


def test_book_stays_sane():
    r = run_once(seed=0)
    book = r["book"]
    assert book.best_bid() < book.best_ask()


def test_events_in_order():
    r = run_once(seed=0)
    times = [t.timestamp for t in r["trades"]]
    assert times == sorted(times)