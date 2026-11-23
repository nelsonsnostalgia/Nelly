from nelly.config import Config
from nelly.ebay import clean_title, inventory_item_body, offer_body, Ebay, EbayError
from nelly.shopify import item_from_node, nelly_sku_for
from nelly.sync import Listing, ebay_sold_skus, plan_takedowns

import pytest

NODE = {
    "id": "gid://shopify/Product/15501902545030",
    "title": "Vintage Sterling Silver Manatee Pendant Charm sea Cow Souvenir",
    "status": "ACTIVE",
    "vendor": "Unknown",
    "tags": ["vintage jewelry"],
    "descriptionHtml": "<p>Sterling silver manatee.<br>About 1 inch.</p>",
    "media": {"nodes": [{"image": {"url": "https://cdn.example/a.jpg"}}, {}]},
    "variants": {"nodes": [{
        "sku": "03 BIn 18", "price": "24.95", "inventoryQuantity": 1,
        "inventoryItem": {"id": "gid://shopify/InventoryItem/1",
                          "unitCost": None,
                          "measurement": {"weight": {"value": 4, "unit": "OUNCES"}}},
    }]},
}


def cfg(**kw):
    base = Config.from_env()
    return Config(**{**base.__dict__, **kw})


def test_item_mapping_uses_unique_sku_and_default_cogs():
    item = item_from_node(NODE, default_cogs=1.0)
    assert item.nelly_sku == "NN-15501902545030"
    assert item.shelf_spot == "03 BIn 18"
    assert item.cogs == 1.0 and item.cogs_is_default
    assert item.weight_lb == 0.25
    assert item.image_urls == ["https://cdn.example/a.jpg"]


def test_real_cost_kept():
    node = {**NODE, "variants": {"nodes": [{**NODE["variants"]["nodes"][0],
            "inventoryItem": {"unitCost": {"amount": "14.03"}}}]}}
    item = item_from_node(node, 1.0)
    assert item.cogs == 14.03 and not item.cogs_is_default


def test_title_cut_at_word_under_80():
    long = "Vintage " * 15
    t = clean_title(long)
    assert len(t) <= 80 and not t.endswith(" ")
    assert clean_title("Short title") == "Short title"


def test_ebay_bodies():
    item = item_from_node(NODE, 1.0)
    inv = inventory_item_body(item)
    assert inv["availability"]["shipToLocationAvailability"]["quantity"] == 1
    assert inv["packageWeightAndSize"]["weight"] == {"value": 0.25, "unit": "POUND"}
    assert "brand" not in inv["product"]  # "Unknown" vendor is not a brand
    off = offer_body(item, cfg(), "12345", {"fulfillment": "f", "payment": "p", "return": "r"})
    assert off["sku"] == "NN-15501902545030"
    assert off["pricingSummary"]["price"] == {"value": "24.95", "currency": "USD"}
    assert off["format"] == "FIXED_PRICE"


def test_publish_blocked_when_off():
    e = Ebay(cfg(publish_enabled=False))
    with pytest.raises(EbayError):
        e.publish("offer-1")


def test_sold_skus_skip_cancelled_and_unpaid():
    orders = [
        {"orderPaymentStatus": "PAID", "cancelStatus": {"cancelState": "NONE_REQUESTED"},
         "lineItems": [{"sku": "NN-1"}]},
        {"orderPaymentStatus": "PAID", "cancelStatus": {"cancelState": "CANCELED"},
         "lineItems": [{"sku": "NN-2"}]},
        {"orderPaymentStatus": "PENDING", "lineItems": [{"sku": "NN-3"}]},
    ]
    assert ebay_sold_skus(orders) == {"NN-1"}


def test_takedowns_never_touch_site_it_sold_on():
    listings = {
        "NN-1": Listing("NN-1", ebay_offer_id="o1", shopify_product_id="p1"),
        "NN-2": Listing("NN-2", ebay_offer_id="o2", shopify_product_id="p2"),
        "NN-3": Listing("NN-3", ebay_offer_id="o3", sold_on="ebay"),
    }
    got = plan_takedowns({"NN-1": "ebay", "NN-2": "shopify", "NN-3": "shopify"}, listings)
    assert got == [("shopify", "NN-1"), ("ebay", "NN-2")]


def test_nelly_sku():
    assert nelly_sku_for("gid://shopify/Product/42") == "NN-42"
