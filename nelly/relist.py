"""Daily delist / relist ("refresh") picker.

Diane's rule (11/27): about 10 items a day. Take the oldest stale listings, end them,
and put them back up fresh on the same site. Protect rare pieces that have watchers,
because a fresh listing starts watchers back at zero.

What each site allows (checked 11/27/2026):
- eBay:     end, then relist as a new listing. Never two live fixed-price copies at once
            (duplicate listings policy). Watchers, views and sales history reset.
            Rare item with watchers: send an offer to watchers instead of relisting.
- Etsy:     use RENEW ($0.20). Keeps views, favorites and the web address. Do not copy.
- Facebook: use RENEW (free). Saves and shares reset. Leave items with open chats alone.
- Whatnot:  delist, then repost. No posted limit; keep each item to once every 60 days.
- Poshmark: delete/relist penalty retired 7/23/2026. Later only; keep it small.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from .markdown import SEASON_STEP, next_price, no_markdown
from .seasons import in_season, last_end, window

DAILY_LIMIT = 10

# How old a listing must be, and how long since its last refresh, before we touch it (days).
MIN_AGE = {"ebay": 60, "etsy": 30, "facebook": 7, "whatnot": 60, "poshmark": 30}
METHOD = {"ebay": "end_and_relist", "etsy": "renew", "facebook": "renew",
          "whatnot": "delist_and_repost", "poshmark": "delist_and_repost"}
COST = {"etsy": 0.20}   # money each refresh costs us

PROTECT_PRICE = 100.0     # $100 and up counts as high value
PROTECT_WATCHERS = 3      # this many watchers/favorites = someone is saving up for it


@dataclass
class Live:
    sku: str
    title: str
    site: str
    listing_id: str
    price: float
    listed_on: date
    watchers: int = 0             # eBay watchers / Etsy favorites / FB saves
    open_chats: int = 0           # unanswered messages or open offers
    protected: bool = False       # Diane/Eric tapped "Protect"
    cost: float | None = None     # what we paid (for the markdown floor)
    original: float | None = None # first price, for the 50%-off limit
    season: str | None = None     # Christmas, Halloween ... (None = everyday item)
    season_marked: date | None = None  # last after-season markdown
    refreshes: list[tuple[date, str, str]] = field(default_factory=list)  # (day, old id, new id)

    @property
    def last_fresh(self) -> date:
        return self.refreshes[-1][0] if self.refreshes else self.listed_on


def protect_reason(x: Live) -> str | None:
    """Why this listing should NOT be relisted, or None if it's fine."""
    if x.protected:
        return "Protected"
    if x.open_chats:
        return "Open message or offer"
    if x.watchers >= PROTECT_WATCHERS or (x.watchers and x.price >= PROTECT_PRICE):
        return "Has watchers (send them an offer instead)" if x.site == "ebay" else "Has favorites/saves"
    return None


def pick(listings: list[Live], today: date, limit: int = DAILY_LIMIT,
         sites: tuple[str, ...] = ("ebay", "etsy", "whatnot", "facebook")):
    """Return (to_refresh, held_back). Season openers first, then oldest; ties go to higher price."""
    due, held = [], []
    for x in listings:
        if x.site not in sites:
            continue
        opener = False
        if x.season:
            start, end = window(x.season, today)
            if not in_season(x.season, today):
                held.append((x, f"Saving for {x.season} (season starts {start:%b %-d})"))
                continue
            opener = x.last_fresh < start          # first relist of this season
        if not opener and (today - x.last_fresh).days < MIN_AGE[x.site]:
            continue
        why = protect_reason(x)
        if why:
            held.append((x, why))
        else:
            due.append((x, why, opener))
    due.sort(key=lambda t: (not t[2], t[0].last_fresh, -t[0].price))
    return [x for x, _, _ in due[:limit]], held


def plan(listings, today, limit=DAILY_LIMIT, **kw) -> list[dict]:
    """Plain-English daily plan, one line per item."""
    go, held = pick(listings, today, limit, **kw)
    rows = []
    for x in go:
        if x.season:                               # seasonal: full price, never marked down
            new, why = None, f"{x.season} item, kept at full price"
        else:
            new, why = next_price(x.price, x.cost, original=x.original)   # about 5% off with each relist
        rows.append({"sku": x.sku, "site": x.site, "do": METHOD[x.site], "fee": COST.get(x.site, 0.0),
                     "age_days": (today - x.last_fresh).days, "title": x.title,
                     "new_price": float(new) if new else x.price, "price_note": why,
                     "decide": new is None and not x.season and not no_markdown(x.price)})   # hit the floor/limit -> goes on Eric's decide list
    rows += [{"sku": x.sku, "site": x.site, "do": "hold", "why": why, "title": x.title}
             for x, why in held]
    return rows


def record(x: Live, today: date, new_id: str) -> None:
    """Keep the relist history on the item."""
    x.refreshes.append((today, x.listing_id, new_id))
    x.listing_id = new_id


def season_markdowns(listings: list[Live], today: date) -> list[dict]:
    """Seasonal items still unsold after their season: one 20% markdown, once per season.
    Items first listed after the season ended are left at full price until the next one ends."""
    rows = []
    for x in listings:
        if not x.season or in_season(x.season, today):
            continue
        end = last_end(x.season, today)
        if not end or x.listed_on > end or (x.season_marked and x.season_marked > end):
            continue
        new, why = next_price(x.price, x.cost, step=SEASON_STEP, original=x.original)
        rows.append({"sku": x.sku, "site": x.site, "title": x.title, "do": "price_change",
                     "new_price": float(new) if new else x.price,
                     "price_note": f"After {x.season}: " + why,
                     "decide": new is None and not no_markdown(x.price)})
    return rows
