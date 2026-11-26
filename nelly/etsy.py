"""Etsy connection: sign-in, draft listings, photos, take down, read orders.

Uses Etsy Open API v3. New listings are always created as drafts. Going live
needs NELLY_PUBLISH=true, same rule as eBay.
"""
from __future__ import annotations

import base64
import hashlib
import re
import secrets
import time
import urllib.parse

import requests

from .config import Config
from .ebay import plain_text
from .shopify import Item
from . import words
from .cards import card_for, measurements_block

API = "https://openapi.etsy.com/v3/application"
CONNECT = "https://www.etsy.com/oauth/connect"
TOKEN = "https://api.etsy.com/v3/public/oauth/token"
SCOPES = ["listings_r", "listings_w", "listings_d", "shops_r", "transactions_r"]

TITLE_MAX = 140
TAG_MAX_LEN = 20
TAG_MAX = 13


class EtsyError(RuntimeError):
    pass


# ---------- sign-in (OAuth with PKCE) ----------

def new_verifier() -> str:
    return secrets.token_urlsafe(48)


def challenge_for(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def consent_url(cfg: Config, verifier: str, state: str = "nelly") -> str:
    q = {
        "response_type": "code",
        "client_id": cfg.etsy_keystring,
        "redirect_uri": cfg.etsy_redirect_uri,
        "scope": " ".join(SCOPES),
        "state": state,
        "code_challenge": challenge_for(verifier),
        "code_challenge_method": "S256",
    }
    return CONNECT + "?" + urllib.parse.urlencode(q, quote_via=urllib.parse.quote)


def exchange_code(cfg: Config, code: str, verifier: str, http=None) -> dict:
    r = (http or requests).post(TOKEN, data={
        "grant_type": "authorization_code", "client_id": cfg.etsy_keystring,
        "redirect_uri": cfg.etsy_redirect_uri, "code": code,
        "code_verifier": verifier,
    }, timeout=30)
    if r.status_code != 200:
        raise EtsyError(f"Etsy sign-in failed: {r.status_code} {r.text[:300]}")
    return r.json()  # holds refresh_token; store it as ETSY_REFRESH_TOKEN


# ---------- listing text ----------

def clean_title(title: str) -> str:
    """Etsy titles: max 140 characters, and only one each of %, : and &."""
    t = re.sub(r"\s+", " ", title).strip()
    for ch in "%:&":
        first = t.find(ch)
        if first != -1:
            t = t[:first + 1] + t[first + 1:].replace(ch, " ")
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) > TITLE_MAX:
        t = t[:TITLE_MAX].rsplit(" ", 1)[0] or t[:TITLE_MAX]
    return t


def clean_tags(tags: list[str]) -> list[str]:
    """Etsy allows 13 tags of up to 20 letters, numbers and spaces."""
    out: list[str] = []
    for tag in tags:
        t = re.sub(r"[^A-Za-z0-9 \-']", " ", tag)
        t = re.sub(r"\s+", " ", t).strip()
        if len(t) > TAG_MAX_LEN:  # cut at a whole word
            t = t[:TAG_MAX_LEN + 1].rsplit(" ", 1)[0].strip() or t[:TAG_MAX_LEN]
        if t and t.lower() not in {x.lower() for x in out}:
            out.append(t)
        if len(out) == TAG_MAX:
            break
    return out


def listing_description(item: Item, measures: dict[str, str] | None = None) -> str:
    text = plain_text(item.description_html) or item.title
    card = card_for(item.title, item.tags)
    block = measurements_block(card, measures or {}) if card else ""
    return words.clean(text + ("\n\n" + block if block else ""))


def listing_body(item: Item, cfg: Config, taxonomy_id: int,
                 measures: dict[str, str] | None = None) -> dict:
    body = {
        "quantity": max(item.quantity, 1),
        "title": clean_title(words.clean(item.title)),
        "description": listing_description(item, measures),
        "price": round(item.price, 2),
        "who_made": "someone_else",   # vintage: made by someone else
        "when_made": "before_2007",   # Etsy vintage = 20+ years old
        "taxonomy_id": taxonomy_id,
        "type": "physical",
        "tags": ",".join(clean_tags([words.clean(t) for t in item.tags])),  # Etsy wants one comma list
        "should_auto_renew": False,
    }
    if cfg.etsy_readiness_state_id:
        body["readiness_state_id"] = int(cfg.etsy_readiness_state_id)
    if cfg.etsy_shipping_profile_id:
        body["shipping_profile_id"] = int(cfg.etsy_shipping_profile_id)
    if item.weight_lb:
        body["item_weight"] = round(item.weight_lb, 2)
        body["item_weight_unit"] = "lb"
        # Etsy's calculated shipping needs box size. Until the box list is in
        # NELLY, use a standard box by weight.
        length, width, height = box_for(item.weight_lb)
        body.update(item_length=length, item_width=width, item_height=height,
                    item_dimensions_unit="in")
    return body


def box_for(weight_lb: float) -> tuple[int, int, int]:
    """Standard box (inches) by packed weight."""
    if weight_lb <= 1:
        return (9, 6, 3)
    if weight_lb <= 3:
        return (12, 9, 4)
    if weight_lb <= 10:
        return (14, 12, 8)
    return (18, 14, 12)


# ---------- API client ----------

class Etsy:
    def __init__(self, cfg: Config, http: requests.Session | None = None):
        self.cfg = cfg
        self.http = http or requests.Session()
        self._token: tuple[str, float] | None = None

    def api_key(self) -> str:
        # Etsy asks for "keystring:shared secret" in the x-api-key header.
        k, s = self.cfg.etsy_keystring, self.cfg.etsy_shared_secret
        return f"{k}:{s}" if s else k

    def user_token(self) -> str:
        if self._token and self._token[1] > time.time() + 60:
            return self._token[0]
        if not self.cfg.etsy_refresh_token:
            raise EtsyError("No Etsy sign-in yet. Open the Etsy sign-in link first.")
        r = self.http.post(TOKEN, data={
            "grant_type": "refresh_token", "client_id": self.cfg.etsy_keystring,
            "refresh_token": self.cfg.etsy_refresh_token,
        }, timeout=30)
        if r.status_code != 200:
            raise EtsyError(f"Etsy token failed: {r.status_code} {r.text[:300]}")
        body = r.json()
        self._token = (body["access_token"], time.time() + body["expires_in"])
        return body["access_token"]

    def _call(self, method: str, path: str, *, auth: bool = True, **kw):
        # If the shared secret is not in our settings, the network secret
        # adds the x-api-key header for us.
        headers = {"x-api-key": self.api_key()} if self.cfg.etsy_shared_secret else {}
        if method in ("POST", "PATCH", "PUT") and isinstance(kw.get("data"), dict):
            d = kw["data"]
            words.check(str(d.get("title", "")), str(d.get("description", "")),
                        str(d.get("tags", "")))
        if auth:
            headers["Authorization"] = f"Bearer {self.user_token()}"
        r = self.http.request(method, API + path, headers=headers, timeout=60, **kw)
        if r.status_code not in (200, 201, 204):
            raise EtsyError(f"{method} {path} -> {r.status_code}: {r.text[:500]}")
        return r.json() if r.content else {}

    def shop_id(self) -> str:
        return self.cfg.etsy_shop_id or str(self._call("GET", "/users/me")["shop_id"])

    def shipping_profiles(self) -> list[dict]:
        return self._call("GET", f"/shops/{self.shop_id()}/shipping-profiles").get("results", [])

    def ready_to_ship_id(self) -> int:
        """Etsy needs a 'ready to ship' processing time on physical items."""
        data = self._call("GET", f"/shops/{self.shop_id()}/readiness-state-definitions")
        for r in data.get("results", []):
            if r.get("readiness_state") == "ready_to_ship":
                return r["readiness_state_id"]
        raise EtsyError("No 'ready to ship' processing time set up in the Etsy shop.")

    def save_draft(self, item: Item, taxonomy_id: int,
                   measures: dict[str, str] | None = None) -> dict:
        """Make a draft listing, its photos, and the measurement card picture.
        Not live."""
        shop = self.shop_id()
        body = listing_body(item, self.cfg, taxonomy_id, measures)
        body.setdefault("readiness_state_id", self.ready_to_ship_id())
        listing = self._call("POST", f"/shops/{shop}/listings", data=body)
        lid = listing["listing_id"]
        self.set_sku(lid, item.nelly_sku)
        card = card_for(item.title, item.tags)
        photos = item.image_urls[: 9 if card and measures else 10]
        for rank, url in enumerate(photos, start=1):
            img = self.http.get(url, timeout=60)
            img.raise_for_status()
            self._call("POST", f"/shops/{shop}/listings/{lid}/images",
                       files={"image": (f"{item.nelly_sku}-{rank}.jpg", img.content)},
                       data={"rank": rank})
        if card and measures:
            self.add_card_picture(lid, item, card, measures, rank=len(photos) + 1)
        return {"sku": item.nelly_sku, "listingId": lid, "state": listing.get("state")}

    def add_card_picture(self, listing_id: int, item: Item, card: dict,
                         measures: dict[str, str], rank: int) -> None:
        """Add the filled-in measurement card as a listing photo."""
        import tempfile
        from pathlib import Path
        from .card_image import make
        with tempfile.TemporaryDirectory() as tmp:
            path = make(card, measures, Path(tmp) / f"{item.nelly_sku}-card.jpg")
            self._call("POST", f"/shops/{self.shop_id()}/listings/{listing_id}/images",
                       files={"image": (path.name, path.read_bytes())},
                       data={"rank": rank})

    def set_sku(self, listing_id: int, sku: str) -> None:
        """Etsy keeps the SKU on the listing's inventory, not the listing."""
        inv = self._call("GET", f"/listings/{listing_id}/inventory")
        products = []
        for p in inv["products"]:
            products.append({"sku": sku, "property_values": p.get("property_values", []),
                             "offerings": [{
                                 "price": o["price"]["amount"] / o["price"]["divisor"],
                                 "quantity": o["quantity"], "is_enabled": o["is_enabled"],
                                 "readiness_state_id": o["readiness_state_id"],
                             } for o in p["offerings"]]})
        self._call("PUT", f"/listings/{listing_id}/inventory", json={"products": products})

    def set_state(self, listing_id: int, state: str) -> None:
        if state == "active" and not self.cfg.publish_enabled:
            raise EtsyError("Publishing is turned off (NELLY_PUBLISH=false). Draft only.")
        self._call("PATCH", f"/shops/{self.shop_id()}/listings/{listing_id}",
                   data={"state": state})

    def end_listing(self, listing_id: int) -> None:
        """Take down a listing (sold somewhere else). Keeps it as inactive."""
        self.set_state(listing_id, "inactive")

    def recent_receipts(self, since_unix: int) -> list[dict]:
        data = self._call("GET", f"/shops/{self.shop_id()}/receipts",
                          params={"min_created": since_unix, "was_paid": "true",
                                  "limit": 100})
        return data.get("results", [])


def etsy_sold_skus(receipts: list[dict]) -> set[str]:
    """SKUs from paid Etsy orders that were not cancelled."""
    out = set()
    for rc in receipts:
        if not rc.get("is_paid") or rc.get("status", "").lower() == "canceled":
            continue
        for t in rc.get("transactions", []):
            if t.get("sku"):
                out.add(t["sku"])
    return out
