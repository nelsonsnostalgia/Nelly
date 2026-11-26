"""eBay connection: sign-in, drafts, publish, end listing, read orders.

Uses eBay's official Sell APIs (Inventory, Account, Fulfillment) and the
Taxonomy API for category suggestions. Nothing goes live unless
publish_enabled is turned on in the settings.
"""
from __future__ import annotations

import base64
import html
import re
import time
import urllib.parse

import requests

from .config import Config
from .shopify import Item
from . import words

API = "https://api.ebay.com"
AUTH = "https://auth.ebay.com/oauth2/authorize"
TOKEN = "https://api.ebay.com/identity/v1/oauth2/token"

SCOPES = [
    "https://api.ebay.com/oauth/api_scope",
    "https://api.ebay.com/oauth/api_scope/sell.inventory",
    "https://api.ebay.com/oauth/api_scope/sell.account",
    "https://api.ebay.com/oauth/api_scope/sell.fulfillment",
    "https://api.ebay.com/oauth/api_scope/sell.marketing",
]

TITLE_MAX = 80  # eBay listing title limit


class EbayError(RuntimeError):
    pass


# ---------- sign-in ----------

def consent_url(cfg: Config, state: str = "nelly") -> str:
    """The one link Diane opens to let NELLY act for her eBay seller account."""
    q = {
        "client_id": cfg.ebay_client_id,
        "response_type": "code",
        "redirect_uri": cfg.ebay_ru_name,
        "scope": " ".join(SCOPES),
        "state": state,
    }
    return AUTH + "?" + urllib.parse.urlencode(q, quote_via=urllib.parse.quote)


def _basic(cfg: Config) -> str:
    raw = f"{cfg.ebay_client_id}:{cfg.ebay_client_secret}".encode()
    return "Basic " + base64.b64encode(raw).decode()


def exchange_code(cfg: Config, code: str, http: requests.Session | None = None) -> dict:
    """Trade the code from the sign-in page for a long-lived refresh token."""
    r = (http or requests).post(
        TOKEN,
        headers={"Authorization": _basic(cfg),
                 "Content-Type": "application/x-www-form-urlencoded"},
        data={"grant_type": "authorization_code", "code": code,
              "redirect_uri": cfg.ebay_ru_name},
        timeout=30,
    )
    if r.status_code != 200:
        raise EbayError(f"eBay sign-in failed: {r.status_code} {r.text[:300]}")
    return r.json()  # holds refresh_token; store it as EBAY_REFRESH_TOKEN


# ---------- listing text ----------

def clean_title(title: str) -> str:
    """eBay titles max 80 characters; cut at a word break."""
    t = re.sub(r"\s+", " ", words.clean(title)).strip()
    if len(t) <= TITLE_MAX:
        return t
    cut = t[:TITLE_MAX].rsplit(" ", 1)[0]
    return cut or t[:TITLE_MAX]


def plain_text(description_html: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", description_html, flags=re.I)
    text = re.sub(r"</p>\s*<p>", "\n\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).strip()


def inventory_item_body(item: Item) -> dict:
    body = {
        "availability": {"shipToLocationAvailability": {"quantity": max(item.quantity, 0)}},
        "condition": "USED_EXCELLENT",
        "product": {
            "title": clean_title(item.title),
            "description": words.clean(item.description_html or item.title),
            "imageUrls": item.image_urls[:24],
        },
    }
    if item.vendor and item.vendor.lower() not in {"unknown", "nelsons nostalgia"}:
        body["product"]["brand"] = item.vendor
    if item.weight_lb:
        body["packageWeightAndSize"] = {
            "weight": {"value": round(item.weight_lb, 2), "unit": "POUND"}
        }
    return body


def offer_body(item: Item, cfg: Config, category_id: str, policies: dict) -> dict:
    return {
        "sku": item.nelly_sku,
        "marketplaceId": cfg.ebay_marketplace,
        "format": "FIXED_PRICE",
        "availableQuantity": max(item.quantity, 0),
        "categoryId": category_id,
        "listingDescription": words.clean(item.description_html),
        "listingPolicies": {
            "fulfillmentPolicyId": policies["fulfillment"],
            "paymentPolicyId": policies["payment"],
            "returnPolicyId": policies["return"],
        },
        "pricingSummary": {"price": {"value": f"{item.price:.2f}", "currency": "USD"}},
        "merchantLocationKey": cfg.ebay_location_key,
    }


# ---------- API client ----------

class Ebay:
    def __init__(self, cfg: Config, http: requests.Session | None = None):
        self.cfg = cfg
        self.http = http or requests.Session()
        self._user_token: tuple[str, float] | None = None
        self._app_token: tuple[str, float] | None = None

    # tokens
    def _token(self, grant: dict, cache_attr: str) -> str:
        cached = getattr(self, cache_attr)
        if cached and cached[1] > time.time() + 60:
            return cached[0]
        r = self.http.post(
            TOKEN,
            headers={"Authorization": _basic(self.cfg),
                     "Content-Type": "application/x-www-form-urlencoded"},
            data=grant, timeout=30,
        )
        if r.status_code != 200:
            raise EbayError(f"eBay token failed: {r.status_code} {r.text[:300]}")
        body = r.json()
        setattr(self, cache_attr, (body["access_token"], time.time() + body["expires_in"]))
        return body["access_token"]

    def user_token(self) -> str:
        if not self.cfg.ebay_refresh_token:
            raise EbayError("No eBay sign-in yet. Open the consent link first.")
        return self._token({"grant_type": "refresh_token",
                            "refresh_token": self.cfg.ebay_refresh_token,
                            "scope": " ".join(SCOPES)}, "_user_token")

    def app_token(self) -> str:
        return self._token({"grant_type": "client_credentials",
                            "scope": SCOPES[0]}, "_app_token")

    def _call(self, method: str, path: str, *, app: bool = False, ok=(200, 201, 204), **kw):
        token = self.app_token() if app else self.user_token()
        headers = {"Authorization": f"Bearer {token}",
                   "Content-Type": "application/json",
                   "Content-Language": "en-US",
                   "Accept-Language": "en-US"}
        if method in ("POST", "PUT") and "json" in kw:
            words.check(str(kw["json"]))
        r = self.http.request(method, API + path, headers=headers, timeout=60, **kw)
        if r.status_code not in ok:
            raise EbayError(f"{method} {path} -> {r.status_code}: {r.text[:500]}")
        return r.json() if r.content else {}

    # account setup
    def policies(self) -> dict:
        """First saved Shipping, Payment and Return policy on the account."""
        mp = self.cfg.ebay_marketplace
        out = {}
        for kind, key in (("fulfillment", "fulfillmentPolicies"),
                          ("payment", "paymentPolicies"),
                          ("return", "returnPolicies")):
            data = self._call("GET", f"/sell/account/v1/{kind}_policy",
                              params={"marketplace_id": mp})
            found = data.get(key) or []
            if not found:
                raise EbayError(f"No {kind} business policy on eBay yet.")
            out[kind] = found[0][f"{kind}PolicyId"]
        return out

    def ensure_location(self, city: str, state: str, zip_code: str) -> None:
        key = self.cfg.ebay_location_key
        try:
            self._call("GET", f"/sell/inventory/v1/location/{key}")
        except EbayError:
            self._call("POST", f"/sell/inventory/v1/location/{key}", json={
                "location": {"address": {"city": city, "stateOrProvince": state,
                                         "postalCode": zip_code, "country": "US"}},
                "name": "Nelsons Nostalgia",
                "merchantLocationStatus": "ENABLED",
                "locationTypes": ["WAREHOUSE"],
            })

    def suggest_category(self, title: str) -> str:
        data = self._call("GET", "/commerce/taxonomy/v1/category_tree/0/get_category_suggestions",
                          app=True, params={"q": clean_title(title)})
        sugg = data.get("categorySuggestions") or []
        if not sugg:
            raise EbayError(f"No eBay category found for: {title}")
        return sugg[0]["category"]["categoryId"]

    # drafts and listings
    def save_draft(self, item: Item, policies: dict, category_id: str | None = None) -> dict:
        """Create or update the item and its offer on eBay. Not live."""
        sku = urllib.parse.quote(item.nelly_sku, safe="")
        self._call("PUT", f"/sell/inventory/v1/inventory_item/{sku}",
                   json=inventory_item_body(item))
        category_id = category_id or self.suggest_category(item.title)
        body = offer_body(item, self.cfg, category_id, policies)
        existing = self._call("GET", "/sell/inventory/v1/offer",
                              params={"sku": item.nelly_sku}, ok=(200, 404))
        offers = existing.get("offers") or []
        if offers:
            offer_id = offers[0]["offerId"]
            self._call("PUT", f"/sell/inventory/v1/offer/{offer_id}", json=body)
        else:
            offer_id = self._call("POST", "/sell/inventory/v1/offer", json=body)["offerId"]
        return {"sku": item.nelly_sku, "offerId": offer_id, "categoryId": category_id}

    def publish(self, offer_id: str) -> str:
        if not self.cfg.publish_enabled:
            raise EbayError("Publishing is turned off (NELLY_PUBLISH=false). Draft only.")
        return self._call("POST", f"/sell/inventory/v1/offer/{offer_id}/publish")["listingId"]

    def end_listing(self, offer_id: str) -> None:
        """End a live listing (item sold somewhere else). Keeps the record."""
        self._call("POST", f"/sell/inventory/v1/offer/{offer_id}/withdraw")

    def set_price(self, item: Item, offer_id: str, new_price: float, floor: float) -> float:
        """Markdown that never goes below the item's price floor."""
        price = max(round(new_price, 2), floor)
        self._call("POST", "/sell/inventory/v1/bulk_update_price_quantity", json={
            "requests": [{"sku": item.nelly_sku, "offers": [{
                "offerId": offer_id,
                "price": {"value": f"{price:.2f}", "currency": "USD"},
            }]}],
        })
        return price

    def recent_orders(self, since_iso: str) -> list[dict]:
        data = self._call("GET", "/sell/fulfillment/v1/order",
                          params={"filter": f"creationdate:[{since_iso}..]", "limit": 200})
        return data.get("orders") or []

    def migrate_listings(self, listing_ids: list[str]) -> dict:
        """Bring listings made by List Perfectly under NELLY, so we never
        create a second copy of an item that is already on eBay."""
        return self._call("POST", "/sell/inventory/v1/bulk_migrate_listing", json={
            "requests": [{"listingId": lid} for lid in listing_ids[:5]],
        })
