Jul 31 — limit order book, all six tests passing.

the hard part wasn't the matching, it was the gap between understanding what a limit order book is and knowing what to actually build. i learned it in theory but wasn't sure what data structure to implement.

first tried structuring the crossing loop around the conditions for when it crosses. found it complex with a lot of edge cases, so negating it seemed like a better fit.

then with some research worked out the three structures:

sorted dict for price levels — need the best price cheaply, and ordered iteration so i can walk deeper when one level isn't enough
deque at each price — time priority means oldest fills first, so popleft not pop
plain dict of order id → order — so cancel is O(1) instead of scanning the whole book

had to map out all the edge cases on paper before writing anything. once i could trace it by hand the loop was obvious.

two things i got wrong:

thought a buy at 100 hitting a resting sell at 95 filled at 100. it fills at 95 — the limit is a ceiling, not the price you pay, the resting order sets it.
with cancel, the price level has to be removed too, not just the order it points to. otherwise best_ask returns a price with nothing behind it and the book lies about itself. intuitively it makes sense, but it's something i only hit while actually building it.