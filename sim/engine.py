import heapq


class Engine:
    def __init__(self):
        self.clock = 0.0
        self.events = []     # heap of (timestamp, seq, callback)
        self.seq = 0
        self.order_id = 0

    def schedule(self, delay, callback):
        """Put a callback on the queue, `delay` from now."""
        timestamp = self.clock + delay
        heapq.heappush(self.events, (timestamp,self.seq,callback))
        self.seq = self.seq + 1

    def run(self, until):
        """Pop the earliest, advance the clock, call it."""
        while self.events:
            timestamp, seq, callback = heapq.heappop(self.events)

            if timestamp > until:
                break
            self.clock = timestamp
            callback()
    
    def next_order_id(self):
        """Return a unique order id."""
        self.order_id = self.order_id + 1
        return self.order_id 

