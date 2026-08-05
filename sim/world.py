import numpy as np
import math
#random walk

class World:
    def __init__(self,rng,fair_value=50.0,sigma=0.1, T=1000):
        self.fair_value = fair_value
        self.sigma = sigma
        self.T = T
        self.rng = rng

    def step(self):
        """Advance fair value by one random increment."""
        p = self.fair_value / 100               # 1. price to probability
        z = math.log(p / (1 - p))               # 2. probability to log-odds
        z = z + self.sigma * self.rng.normal()  # 3. the walk happens here
        p = 1 / (1 + math.exp(-z))              # 4. log-odds back to probability
        self.fair_value = p * 100             
        return self.fair_value

    def time_remaining(self, now):
        """How long until the market resolves."""
        return max(0, self.T - now)

    def resolve(self):
        p = self.fair_value/100
        event_occurred = 0
        draw = self.rng.random()
        if p > draw:
            event_occurred = 100
        else:
            event_occurred = 0
        return event_occurred
