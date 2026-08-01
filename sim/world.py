import numpy as np
#random walk

class World:
    def __init__(self,rng,fair_value=50.0,sigma=0.5, T=1000):
        self.fair_value = fair_value
        self.sigma = sigma
        self.T = T
        self.rng = rng

    def step(self):
        """Advance fair value by one random increment."""
        self.fair_value = self.rng.normal()*self.sigma + self.fair_value
        return self.fair_value

    def time_remaining(self, now):
        """How long until the market resolves."""
        return max(0, self.T - now)



w = World(np.random.default_rng(42))
for _ in range(20):
    print(round(w.step(), 2))