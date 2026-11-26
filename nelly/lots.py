"""Neil's auction lots: find what we paid and split it across the pieces.

Max writes on the bin sheet:  Neil's 50362-246, 1 of 3
  50362 = invoice number, 246 = lot number, 1 of 3 = this piece and how many pieces.

Diane's rule (11/26, option B): split the lot's all-in cost by each piece's price.
- Only pieces that are actually listed share the cost (unlisted pieces add theirs to the rest).
- Sold pieces keep the cost they had; only unsold pieces get re-split when a new piece is added.
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

DEFAULT_CSV = Path("/mnt/project-files/nelly/neils_purchases_cogs.csv")
NOTE = re.compile(r"neil'?s\D*(\d+)\s*-\s*(\d+)(?:\D+(\d+)\s*of\s*(\d+))?", re.I)
CENT = Decimal("0.01")


@dataclass
class LotTag:
    invoice: str
    lot: str
    piece: int | None = None
    of: int | None = None

    @property
    def key(self) -> tuple[str, str]:
        return (self.invoice, self.lot)

    def label(self) -> str:
        s = f"Neil's {self.invoice}-{self.lot}"
        return s + (f", {self.piece} of {self.of}" if self.piece else "")


@dataclass
class Lot:
    invoice: str
    lot: str
    title: str
    all_in: Decimal
    date: str


def read_note(text: str) -> LotTag | None:
    """Pull 'Neil's 50362-246, 1 of 3' out of bin sheet text. None if not a Neil's item."""
    m = NOTE.search(text or "")
    if not m:
        return None
    inv, lot, piece, of = m.groups()
    return LotTag(inv, lot, int(piece) if piece else None, int(of) if of else None)


def load(path: Path | str = DEFAULT_CSV) -> dict[tuple[str, str], Lot]:
    with open(path, newline="") as f:
        return {
            (r["invoice_number"], r["lot"]): Lot(r["invoice_number"], r["lot"], r["item_title"],
                                                 Decimal(r["all_in_cost"]), r["invoice_date"])
            for r in csv.DictReader(f)
        }


def split(all_in, pieces: list[dict]) -> dict[str, Decimal]:
    """Give each listed piece its share of the lot cost.

    pieces: [{"sku": ..., "price": ..., "sold": bool, "cost": existing cost if sold}]
    Returns {sku: cost}. Sold pieces keep their cost; the rest is split by price.
    Pennies left over from rounding go to the highest-priced piece so it always adds up.
    """
    total = Decimal(str(all_in))
    sold = [p for p in pieces if p.get("sold")]
    open_ = [p for p in pieces if not p.get("sold")]
    out = {p["sku"]: Decimal(str(p["cost"])).quantize(CENT) for p in sold}
    left = max(total - sum(out.values(), Decimal(0)), Decimal(0))
    if not open_:
        return out
    prices = [Decimal(str(p["price"])) for p in open_]
    psum = sum(prices)
    for p, price in zip(open_, prices):
        share = left * price / psum if psum else left / len(open_)
        out[p["sku"]] = share.quantize(CENT, ROUND_HALF_UP)
    diff = left - sum(out[p["sku"]] for p in open_)
    top = max(open_, key=lambda p: Decimal(str(p["price"])))
    out[top["sku"]] += diff
    return out
