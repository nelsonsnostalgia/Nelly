"""Price markdowns tied to the daily relist.

Diane's idea (11/27):
- Every price starts with a .99 ending.
- Each time an item is relisted it drops about 5%, and the cents drop by one:
  .99 = never marked down, .98 = once, .97 = twice, .96 = three times ...
  So the cents tell you how many markdowns it has had.
- "At least 5%": we round DOWN to the next whole dollar, so cheap items may drop a bit more.

Limits (recommended, waiting on Diane's OK):
- Stop after MAX_MARKDOWNS (5 = cents .94, about 25% off).
- Never go below FLOOR_X times what we paid, and never below FLOOR_MIN dollars.
- When an item hits a limit it goes on Eric's "decide" list (bundle, lot, donate, or keep).
"""
from __future__ import annotations

import math
from decimal import Decimal

STEP = 0.05
MAX_MARKDOWNS = 5
FLOOR_X = 2.0          # never below 2x cost
FLOOR_MIN = 5.00       # never below $5


def _d(x) -> Decimal:
    return Decimal(str(x)).quantize(Decimal("0.01"))


def start_price(p) -> Decimal:
    """Any price -> nearest .99 price (24.50 -> 24.99, 25.10 -> 24.99)."""
    return _d(max(round(float(p) + 0.01), 1) - 0.01)


def times_marked(price) -> int:
    """How many markdowns, read from the cents (.99 = 0, .97 = 2). Off-pattern prices = 0."""
    cents = int(round(float(price) * 100)) % 100
    return 99 - cents if 90 <= cents <= 99 else 0


def floor_price(cost) -> Decimal:
    return _d(max(float(cost or 0) * FLOOR_X, FLOOR_MIN))


def next_price(price, cost=None) -> tuple[Decimal | None, str]:
    """Price after one more markdown, or (None, why) when it should not go lower."""
    n = times_marked(price)
    if n >= MAX_MARKDOWNS:
        return None, f"Already marked down {n} times"
    cents = (98 - n) / 100
    target = float(price) * (1 - STEP)
    new = math.floor(target - cents) + cents
    if new >= float(price):
        new -= 1
    new = _d(new)
    fl = floor_price(cost)
    if new < fl:
        return None, f"Would go below floor ${fl}"
    return new, f"Markdown {n + 1}: ${_d(price)} to ${new}"
