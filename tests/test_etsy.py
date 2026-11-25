from nelly.config import Config
from nelly.etsy import (clean_title, clean_tags, listing_body, challenge_for,
                        Etsy, EtsyError, etsy_sold_skus)
from nelly.shopify import item_from_node
from nelly.sync import Listing, plan_takedowns
from tests.test_core import NODE

import pytest


def cfg(**kw):
    return Config(**{**Config.from_env().__dict__, **kw})


def test_title_rules():
    assert clean_title("Pin: Gold & Silver: Rare & Old") == "Pin: Gold & Silver Rare Old"
    assert len(clean_title("Vintage " * 30)) <= 140


def test_tags():
    tags = clean_tags(["vintage jewelry", "Vintage Jewelry", "sterling silver manatee charm", "a/b"] + [f"t{i}" for i in range(20)])
    assert tags[0] == "vintage jewelry" and len(tags) == 13
    assert all(len(t) <= 20 for t in tags)


def test_listing_body():
    item = item_from_node(NODE, 1.0)
    b = listing_body(item, cfg(etsy_shipping_profile_id="77"), 1234)
    assert b["price"] == 24.95 and b["tags"] == "vintage jewelry"
    assert (b["item_length"], b["item_dimensions_unit"]) == (9, "in")
    assert b["who_made"] == "someone_else" and b["shipping_profile_id"] == 77
    assert "<" not in b["description"]


def test_pkce_challenge_known_value():
    # example from RFC 7636
    assert challenge_for("dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk") == \
        "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"


def test_go_live_blocked_when_off():
    with pytest.raises(EtsyError):
        Etsy(cfg(publish_enabled=False)).set_state(1, "active")


def test_etsy_sold_and_takedown():
    receipts = [{"is_paid": True, "status": "Paid", "transactions": [{"sku": "NN-1"}]},
                {"is_paid": True, "status": "Canceled", "transactions": [{"sku": "NN-2"}]}]
    assert etsy_sold_skus(receipts) == {"NN-1"}
    listings = {"NN-1": Listing("NN-1", ebay_offer_id="o", etsy_listing_id=5, shopify_product_id="p")}
    assert plan_takedowns({"NN-1": "etsy"}, listings) == [("ebay", "NN-1"), ("shopify", "NN-1")]
