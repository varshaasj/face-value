from dataclasses import dataclass
from enum import Enum


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