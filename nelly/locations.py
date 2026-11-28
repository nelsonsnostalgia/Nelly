"""Where an item lives in the storage unit.

Existing Shopify format (SKU field):  "03 BIN 18"   = shelf 03, bin 18
New bin type (Diane 11/28):           "05 TRAY 01"  = shelf 05, tray 01

Trays are numbered, not named by color. The candle-type label stays on the tray front
for people; the number is what NELLY uses. Old labels like "F00191" are not locations.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

KINDS = {"BIN": "Bin", "TRAY": "Tray"}
PATTERN = re.compile(r"^\s*(\d{1,3})\s*(BIN|TRAY)\s*(\d{1,3})\s*$", re.I)


@dataclass(frozen=True)
class Spot:
    shelf: int
    kind: str      # BIN or TRAY
    number: int

    def code(self) -> str:
        return f"{self.shelf:02d} {self.kind} {self.number:02d}"

    def say(self) -> str:
        return f"Shelf {self.shelf}, {KINDS[self.kind]} {self.number}"


def parse(text: str) -> Spot | None:
    m = PATTERN.match(text or "")
    if not m:
        return None
    return Spot(int(m[1]), m[2].upper(), int(m[3]))
