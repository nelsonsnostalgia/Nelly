"""Yard sale / estate sale / thrift hauls: what we paid when we can't price each piece.

How it works (plain words):
1. Drop the receipt, photos, or a video of the haul into Dropbox "/_Nelly Purchases".
   One subfolder per trip is easiest, e.g. "2026-11-28 Smith estate sale".
2. NELLY reads the receipt (or the total you type) and gives the trip a code, like BUY-1128-1.
3. Max writes the code on each bin sheet:  BUY-1128-1, 3 of 20
4. NELLY splits the trip total across the pieces by price (same rule as Neil's lots).
   No receipt and no total = default $1 cost, marked "default".
5. Mileage (Diane 11/28): record round-trip miles for every buying trip or pickup
   (Neil's pickups too). Kept as a separate driving expense for taxes at the IRS
   rate (72.5 cents a mile for 2026). It is NOT added into item cost.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date as _date
from decimal import Decimal

from .lots import LotTag, split  # noqa: F401  (split is the shared price-based rule)

DROPBOX_FOLDER = "/_Nelly Purchases"
IRS_RATE = {2026: Decimal("0.725")}   # IRS business mileage rate per mile; add each new year
NOTE = re.compile(r"\bbuy[\s-]*(\d{4})[\s-]*(\d+)(?:\D+(\d+)\s*of\s*(\d+))?", re.I)


@dataclass
class Purchase:
    code: str                 # BUY-1128-1
    date: str                 # 2026-11-28
    place: str                # "Smith estate sale"
    total: Decimal | None     # all-in paid; None until known
    receipt_files: list[str] = field(default_factory=list)  # Dropbox paths (photos, receipts, video)
    note: str = ""
    miles: float = 0.0        # round trip, for the buying trip or pickup
    driver: str = ""          # who drove

    def mileage_cost(self) -> Decimal:
        """Driving expense for this trip at the IRS rate for that year."""
        year = int(self.date[:4])
        rate = IRS_RATE.get(year) or IRS_RATE[max(IRS_RATE)]
        return (Decimal(str(self.miles)) * rate).quantize(Decimal("0.01"))

    @property
    def cost_known(self) -> bool:
        return self.total is not None


def new_code(date: str, taken: set[str]) -> str:
    """BUY-MMDD-n, next free number for that day."""
    mmdd = date[5:7] + date[8:10]
    n = 1
    while f"BUY-{mmdd}-{n}" in taken:
        n += 1
    return f"BUY-{mmdd}-{n}"


def read_note(text: str) -> LotTag | None:
    """'BUY-1128-1, 3 of 20' on a bin sheet -> tag (invoice='BUY-1128', lot='1')."""
    m = NOTE.search(text or "")
    if not m:
        return None
    mmdd, n, piece, of = m.groups()
    return LotTag(f"BUY-{mmdd}", n, int(piece) if piece else None, int(of) if of else None)


def piece_costs(purchase: Purchase, pieces: list[dict], default_cogs: float = 1.0) -> dict:
    """Cost for each listed piece from this trip. Unknown total -> default cost each."""
    if not purchase.cost_known:
        return {p["sku"]: Decimal(str(default_cogs)) for p in pieces}
    return split(purchase.total, pieces)


def mileage_log(trips: list[Purchase], year: int) -> tuple[list[dict], Decimal, float]:
    """Year-end mileage log for taxes: one row per trip, plus total miles and dollars."""
    rows = [{"date": t.date, "place": t.place, "code": t.code, "miles": t.miles,
             "driver": t.driver, "amount": t.mileage_cost()}
            for t in sorted(trips, key=lambda t: t.date) if t.date.startswith(str(year)) and t.miles]
    return rows, sum((r["amount"] for r in rows), Decimal(0)), sum(r["miles"] for r in rows)
