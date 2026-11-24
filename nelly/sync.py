"""Sold anywhere, ended everywhere.

Run every few minutes. Looks at new eBay orders and new Shopify orders and
makes sure a sold item is taken down on every other site.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Listing:
    """Where one item is listed. Saved by NELLY for each item."""
    nelly_sku: str
    ebay_offer_id: str | None = None
    shopify_product_id: str | None = None
    etsy_listing_id: int | None = None
    sold_on: str | None = None


def ebay_sold_skus(orders: list[dict]) -> set[str]:
    """SKUs from paid eBay orders that are not cancelled."""
    out = set()
    for o in orders:
        if o.get("cancelStatus", {}).get("cancelState") not in (None, "NONE_REQUESTED"):
            continue
        if o.get("orderPaymentStatus") not in ("PAID", "PARTIALLY_REFUNDED"):
            continue
        for line in o.get("lineItems", []):
            if line.get("sku"):
                out.add(line["sku"])
    return out


def plan_takedowns(sold: dict[str, str], listings: dict[str, Listing]) -> list[tuple[str, str]]:
    """Given {sku: site_it_sold_on}, list the (site, sku) take-downs to do.

    Never takes down the site where it sold, and skips items already handled.
    """
    actions = []
    for sku, site in sorted(sold.items()):
        lst = listings.get(sku)
        if not lst or lst.sold_on:
            continue
        if site != "ebay" and lst.ebay_offer_id:
            actions.append(("ebay", sku))
        if site != "etsy" and lst.etsy_listing_id:
            actions.append(("etsy", sku))
        if site != "shopify" and lst.shopify_product_id:
            actions.append(("shopify", sku))
    return actions
