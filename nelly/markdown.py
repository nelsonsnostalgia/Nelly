"""Price markdowns tied to the daily relist.

Diane's idea (11/27):
- Every price starts with a .99 ending.
- Each time an item is relisted it drops about 5%, and the cents drop by one:
  .99 = never marked down, .98 = once, .97 = twice, .96 = three times ...
  So the cents tell you how many markdowns it has had.
- "At least 5%": we round DOWN to the next whole dollar, so cheap items may drop a bit more.

Limits (Diane 11/27):
- Never more than 50% off the original price.
- Any price ending in .00 is Eric's sign: NEVER mark it down.
- Never below what we paid.
- When an item hits a limit it goes on Eric's "decide" list (bundle, lot, donate, or keep).
"""
from __future__ import annotations

import math
from decimal import Decimal

STEP = 0.05
SEASON_STEP = 0.20   # seasonal items: one 20% markdown right after their season ends
MAX_OFF = 0.50       # never more than 50% off the original price


def _d(x) -> Decimal:
    return Decimal(str(x)).quantize(Decimal("0.01"))


def _cents(price) -> int:
    return int(round(float(price) * 100)) % 100


def start_price(p) -> Decimal:
    """Any price -> nearest .99 price (24.50 -> 24.99, 25.10 -> 24.99)."""
    return _d(max(round(float(p) + 0.01), 1) - 0.01)


def no_markdown(price) -> bool:
    """Eric's .00 prices are never marked down."""
    return _cents(price) == 0


def times_marked(price) -> int:
    """How many markdowns, read from the cents (.99 = 0, .97 = 2). Off-pattern prices = 0."""
    c = _cents(price)
    return 99 - c if 80 <= c <= 99 else 0


def floor_price(cost, original=None) -> Decimal:
    """Lowest allowed price: 50% of the original, and never below what we paid."""
    return _d(max(float(cost or 0), float(original or 0) * (1 - MAX_OFF)))


def next_price(price, cost=None, step: float = STEP, original=None) -> tuple[Decimal | None, str]:
    """Price after one more markdown, or (None, why) when it should not go lower."""
    if no_markdown(price):
        return None, "Eric's .00 price, no markdown"
    n = times_marked(price)
    cents = (98 - n) / 100
    target = float(price) * (1 - step)
    new = math.floor(target - cents) + cents
    if new >= float(price):
        new -= 1
    new = _d(new)
    fl = floor_price(cost, original or price)
    if new < fl:
        return None, f"At the lowest allowed price (floor ${fl})"
    return new, f"Markdown {n + 1}: ${_d(price)} to ${new}"
