"""Seasonal items: hold them out of season, push them fresh when their season opens.

Diane (11/27): a Christmas item listed in January should not be marked down or relisted
out of season. Keep it at full price, then relist it fresh as its season comes up.

Each season has a SELLING WINDOW (when buyers shop for it, which starts well before the day).
- Outside the window: no relist, no markdown. Item stays listed at full price.
- Window opens: relist fresh at full price, first in line ahead of the daily 10.
- Inside the window: normal relist timing, but NO markdowns.
"""
from __future__ import annotations

import re
from datetime import date

# name: (start month, start day, end month, end day, keywords)
SEASONS = {
    "Christmas":      (10, 1, 12, 20, "christmas xmas santa noel nativity reindeer ornament stocking nutcracker snowman"),
    "Halloween":      (8, 15, 10, 25, "halloween witch jack-o-lantern pumpkin skeleton ghost bat spooky"),
    "Thanksgiving":   (9, 15, 11, 20, "thanksgiving turkey pilgrim harvest cornucopia"),
    "Easter":         (2, 15, 4, 10, "easter bunny egg chick"),
    "Valentine's":    (1, 2, 2, 10, "valentine cupid sweetheart"),
    "St. Patrick's":  (2, 1, 3, 14, "st patrick shamrock leprechaun irish"),
    "4th of July":    (5, 15, 7, 3, "patriotic july americana uncle-sam firecracker"),
    "Summer":         (4, 1, 7, 31, "beach swimsuit pool picnic cooler hawaiian tiki"),
    "Back to School": (7, 1, 8, 31, "school lunchbox lunch-box pencil-box bookbag"),
    "Winter":         (10, 15, 1, 31, "snow sled ski mittens"),
}


def season_for(title: str, tags=()) -> str | None:
    """Pick a season from the title and tags, or None for everyday items."""
    words = set(re.findall(r"[a-z'\-]+", " ".join([title, *tags]).lower().replace("st. ", "st ")))
    text = " " + " ".join(words) + " "
    for name, (*_, kw) in SEASONS.items():
        if any(k in words or f" {k} " in text for k in kw.split()):
            return name
    return None


def window(name: str, today: date) -> tuple[date, date]:
    """The current or next selling window for a season."""
    sm, sd, em, ed, _ = SEASONS[name]
    for y in (today.year - 1, today.year, today.year + 1):
        start = date(y, sm, sd)
        end = date(y + (1 if (em, ed) < (sm, sd) else 0), em, ed)
        if end >= today:
            return start, end
    raise ValueError(name)


def in_season(name: str, today: date) -> bool:
    start, end = window(name, today)
    return start <= today <= end
