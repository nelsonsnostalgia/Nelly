"""Never sell the same item twice: take it down everywhere else, and keep trying until it's gone.

Diane's #1 rule (11/27): when an item sells on one site, NELLY removes it from every other site.
If a site glitches and the removal fails, NELLY remembers it and tries again until it's
CONFIRMED gone. If it's still stuck, Eric gets an alert. Every morning NELLY also checks
every sold item on every site and re-queues anything still showing as live.

Retry timing: 5 min, 15 min, 1 hour, 4 hours, then once a day, forever, until confirmed.
Eric is alerted when a job has failed for 1 hour, and again each morning it's still stuck.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

RETRY_WAITS = [timedelta(minutes=5), timedelta(minutes=15), timedelta(hours=1), timedelta(hours=4)]
DAILY = timedelta(days=1)
ALERT_AFTER = timedelta(hours=1)


@dataclass
class Job:
    sku: str
    site: str                 # the site to take it DOWN from
    sold_on: str              # where it sold
    created: str              # ISO time it sold
    status: str = "pending"   # pending -> done   (stuck = alerted, still retrying)
    tries: int = 0
    next_try: str = ""
    last_error: str = ""
    history: list[str] = field(default_factory=list)

    @property
    def key(self) -> tuple[str, str]:
        return (self.sku, self.site)


# remove(site, sku) -> None (raise on failure); is_live(site, sku) -> bool
Remover = Callable[[str, str], None]
Checker = Callable[[str, str], bool]


class Queue:
    """Take-down jobs, saved to a file so nothing is forgotten if NELLY restarts."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.jobs: dict[tuple[str, str], Job] = {}
        if self.path.exists():
            for d in json.loads(self.path.read_text()):
                j = Job(**d)
                self.jobs[j.key] = j

    def save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps([asdict(j) for j in self.jobs.values()], indent=1))
        tmp.replace(self.path)

    def add(self, sku: str, sold_on: str, other_sites: list[str], now: datetime) -> list[Job]:
        """An item sold: queue a take-down on every OTHER site it is listed on."""
        new = []
        for site in other_sites:
            if site == sold_on:
                continue
            j = self.jobs.get((sku, site))
            if j and j.status != "done":
                continue                                  # already being handled
            j = Job(sku, site, sold_on, now.isoformat(), next_try=now.isoformat())
            self.jobs[j.key] = j
            new.append(j)
        self.save()
        return new

    def open_jobs(self) -> list[Job]:
        return [j for j in self.jobs.values() if j.status != "done"]

    def run(self, now: datetime, remove: Remover, is_live: Checker) -> list[str]:
        """Try every job that's due. Returns alert lines for Eric (empty = all good)."""
        alerts = []
        for j in self.open_jobs():
            if j.next_try and datetime.fromisoformat(j.next_try) > now:
                continue
            j.tries += 1
            try:
                remove(j.site, j.sku)
                if is_live(j.site, j.sku):                # trust, but check
                    raise RuntimeError("site still shows it as live")
                j.status, j.last_error = "done", ""
                j.history.append(f"{now:%m/%d %H:%M} removed and confirmed")
            except Exception as e:                       # site glitch, timeout, anything
                j.last_error = str(e)[:200]
                j.history.append(f"{now:%m/%d %H:%M} try {j.tries} failed: {j.last_error}")
                wait = RETRY_WAITS[j.tries - 1] if j.tries <= len(RETRY_WAITS) else DAILY
                j.next_try = (now + wait).isoformat()
                stuck_for = now - datetime.fromisoformat(j.created)
                if stuck_for >= ALERT_AFTER and (j.status != "stuck" or wait == DAILY):
                    j.status = "stuck"
                    alerts.append(f"STILL LIVE: {j.sku} sold on {j.sold_on} but could not be removed "
                                  f"from {j.site} ({j.tries} tries). Please take it down by hand. "
                                  f"Error: {j.last_error}")
        self.save()
        return alerts

    def daily_sweep(self, sold: dict[str, str], listed_on: dict[str, list[str]],
                    is_live: Checker, now: datetime) -> list[str]:
        """Morning check: every sold item, every site. Anything still live gets re-queued.

        sold = {sku: site it sold on}; listed_on = {sku: [sites it was ever listed on]}
        """
        found = []
        for sku, sold_site in sold.items():
            for site in listed_on.get(sku, []):
                if site == sold_site:
                    continue
                try:
                    live = is_live(site, sku)
                except Exception:
                    live = True                          # can't tell = assume live and retry
                if live:
                    j = self.jobs.get((sku, site))
                    if j and j.status == "done":
                        j.status, j.next_try = "pending", now.isoformat()
                        j.history.append(f"{now:%m/%d} morning check found it live again")
                    elif not j:
                        self.add(sku, sold_site, [site], now)
                    found.append(f"{sku} still live on {site}")
        self.save()
        return found


def double_sale(sold_events: list[tuple[str, str]]) -> list[str]:
    """Alert if one SKU shows up as sold on two different sites."""
    seen: dict[str, str] = {}
    out = []
    for sku, site in sold_events:
        if sku in seen and seen[sku] != site:
            out.append(f"DOUBLE SALE: {sku} sold on {seen[sku]} AND {site}. Call Eric now.")
        seen.setdefault(sku, site)
    return out
