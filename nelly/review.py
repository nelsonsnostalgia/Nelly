"""Eric's review step: one tap to Approve or Reject each draft.

Flow: Max's photos -> NELLY drafts -> Eric reviews -> Approve lists it on every
fitting site; Reject sends it back to Max with a reason.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

REJECT_REASONS = [
    "Retake photos",
    "Needs research (brand, age, value)",
    "Price is off",
    "Wrong card or measurements",
    "Other",
]

WAITING, APPROVED, REJECTED, LISTED = "waiting", "approved", "rejected", "listed"


@dataclass
class Review:
    nelly_sku: str
    title: str
    price: float
    sites: list[str]
    status: str = WAITING
    reason: str = ""
    note: str = ""
    history: list[tuple[str, str, str]] = field(default_factory=list)  # (when, who, what)

    def _log(self, who: str, what: str) -> None:
        self.history.append((datetime.now(timezone.utc).isoformat(timespec="seconds"), who, what))

    def approve(self, who: str = "Eric") -> None:
        if self.status != WAITING:
            raise ValueError(f"{self.nelly_sku} is {self.status}, not waiting")
        self.status = APPROVED
        self._log(who, "approved")

    def reject(self, reason: str, note: str = "", who: str = "Eric") -> None:
        if reason not in REJECT_REASONS:
            raise ValueError("Pick one of the reject reasons")
        if self.status != WAITING:
            raise ValueError(f"{self.nelly_sku} is {self.status}, not waiting")
        self.status, self.reason, self.note = REJECTED, reason, note
        self._log(who, f"rejected: {reason}" + (f" ({note})" if note else ""))

    def resubmit(self, who: str = "Max") -> None:
        """Max fixed it; it goes back in Eric's list."""
        if self.status != REJECTED:
            raise ValueError("Only rejected items can be sent back")
        self.status, self.reason, self.note = WAITING, "", ""
        self._log(who, "sent back for review")


def sites_for(title: str, description: str, vintage: bool, ebay_ready: bool) -> list[str]:
    """Which sites an approved item goes to, in order of priority.

    eBay takes almost everything. Etsy only takes vintage (20+ years old) or
    handmade, so NELLY only sends vintage items there.
    """
    sites = []
    if ebay_ready:
        sites.append("ebay")
    if vintage:
        sites.append("etsy")
    return sites + ["shopify"]
