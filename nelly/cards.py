"""Nelsons Nostalgia photo cards (Rev 1, 11/16/2026).

Each item kind has a card: which photos to take, in what order, and which
measurements (A, B, C...) to read off the tools. NELLY uses the card to:
  - pick the card for an item,
  - leave photo 1 (bin sheet) out of every listing,
  - write a plain "Measurements" section into the listing description.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

CARDS: list[dict] = json.loads((Path(__file__).with_name("cards.json")).read_text())
BY_ID = {c["id"]: c for c in CARDS}

# Checked first: more specific kinds that share words with broader ones.
_PRIORITY = ["J-04", "J-08", "J-05", "A-05", "A-02", "A-03", "H-03", "H-07", "C-07",
             "C-02", "C-06", "S-02", "S-03", "E-02"]


def _has(text: str, word: str) -> bool:
    return re.search(r"\b" + re.escape(word) + r"s?\b", text) is not None


def card_for(title: str, tags: list[str] | None = None, product_type: str = "") -> dict | None:
    """Best card for an item from its title, type and tags. None if no card fits."""
    for text in (title, product_type, " ".join(tags or [])):
        t = text.lower()
        order = [BY_ID[i] for i in _PRIORITY] + [c for c in CARDS if c["id"] not in _PRIORITY]
        for c in order:
            if any(_has(t, k) for k in c["keywords"]):
                return c
    return None


def measurements_block(card: dict, values: dict[str, str]) -> str:
    """Plain-text measurements for the listing. Only letters with a value are shown."""
    lines = [f"• {card['measurements'][k]}: {v}" for k, v in sorted(values.items())
             if k in card["measurements"] and v]
    if not lines:
        return ""
    return "Measurements (approximate):\n" + "\n".join(lines)


def listing_photos(urls: list[str], first_is_bin_sheet: bool) -> list[str]:
    """Photos for the listing. Photo 1 (bin sheet) is never shown to buyers."""
    return urls[1:] if first_is_bin_sheet else urls
