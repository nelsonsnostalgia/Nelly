"""Read items from the Shopify master list and mark them sold."""
from __future__ import annotations

from dataclasses import dataclass, field

import requests

from .config import Config


@dataclass
class Item:
    """One item in the master list, in the shape NELLY uses everywhere."""
    product_id: str             # gid://shopify/Product/123
    nelly_sku: str              # unique id NELLY uses on every site: NN-123
    shelf_spot: str             # Shopify SKU field holds the bin, e.g. "03 BIN 18"
    title: str
    description_html: str
    price: float
    quantity: int
    weight_lb: float | None
    cogs: float                 # what we paid; default if unknown
    cogs_is_default: bool
    image_urls: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    vendor: str = ""
    status: str = "ACTIVE"
    inventory_item_id: str = ""


def nelly_sku_for(product_id: str) -> str:
    """Shopify's SKU field holds the shelf spot and repeats across items,
    so NELLY makes its own unique id from the Shopify product number."""
    return "NN-" + product_id.rsplit("/", 1)[-1]


_PRODUCT_FIELDS = """
  id title status vendor tags descriptionHtml
  media(first: 12) { nodes { ... on MediaImage { image { url } } } }
  variants(first: 1) { nodes {
    sku price inventoryQuantity
    inventoryItem { id unitCost { amount } measurement { weight { value unit } } }
  } }
"""


def _to_lb(weight: dict | None) -> float | None:
    if not weight:
        return None
    value, unit = float(weight["value"]), weight["unit"]
    return {
        "POUNDS": value,
        "OUNCES": value / 16,
        "KILOGRAMS": value * 2.20462,
        "GRAMS": value * 0.00220462,
    }.get(unit, value)


def item_from_node(node: dict, default_cogs: float) -> Item:
    variant = (node.get("variants", {}).get("nodes") or [{}])[0]
    inv = variant.get("inventoryItem") or {}
    cost = (inv.get("unitCost") or {}).get("amount")
    weight = (inv.get("measurement") or {}).get("weight")
    images = [
        m["image"]["url"]
        for m in node.get("media", {}).get("nodes", [])
        if m and m.get("image")
    ]
    return Item(
        product_id=node["id"],
        nelly_sku=nelly_sku_for(node["id"]),
        shelf_spot=(variant.get("sku") or "").strip(),
        title=node["title"].strip(),
        description_html=node.get("descriptionHtml") or "",
        price=float(variant.get("price") or 0),
        quantity=int(variant.get("inventoryQuantity") or 0),
        weight_lb=_to_lb(weight),
        cogs=float(cost) if cost is not None else default_cogs,
        cogs_is_default=cost is None,
        image_urls=images,
        tags=node.get("tags") or [],
        vendor=node.get("vendor") or "",
        status=node.get("status") or "ACTIVE",
        inventory_item_id=inv.get("id", ""),
    )


class Shopify:
    def __init__(self, cfg: Config, session: requests.Session | None = None):
        self.cfg = cfg
        self.http = session or requests.Session()
        self.url = (
            f"https://{cfg.shopify_store}/admin/api/{cfg.shopify_api_version}/graphql.json"
        )

    def _gql(self, query: str, variables: dict | None = None) -> dict:
        r = self.http.post(
            self.url,
            json={"query": query, "variables": variables or {}},
            headers={"X-Shopify-Access-Token": self.cfg.shopify_token},
            timeout=30,
        )
        r.raise_for_status()
        body = r.json()
        if body.get("errors"):
            raise RuntimeError(f"Shopify error: {body['errors']}")
        return body["data"]

    def get_item(self, product_id: str) -> Item:
        data = self._gql(
            f"query($id: ID!) {{ product(id: $id) {{ {_PRODUCT_FIELDS} }} }}",
            {"id": product_id},
        )
        return item_from_node(data["product"], self.cfg.default_cogs)

    def active_items(self, page_size: int = 50):
        """Every active item with stock, one page at a time."""
        after = None
        while True:
            data = self._gql(
                "query($n: Int!, $after: String) { products(first: $n, after: $after,"
                " query: \"status:active inventory_total:>0\") {"
                f" nodes {{ {_PRODUCT_FIELDS} }} pageInfo {{ hasNextPage endCursor }} }} }}",
                {"n": page_size, "after": after},
            )
            page = data["products"]
            for node in page["nodes"]:
                yield item_from_node(node, self.cfg.default_cogs)
            if not page["pageInfo"]["hasNextPage"]:
                return
            after = page["pageInfo"]["endCursor"]

    def mark_sold(self, item: Item, location_id: str) -> None:
        """Set stock to 0 so the item stops showing on Shopify and Facebook."""
        self._gql(
            "mutation($input: InventorySetQuantitiesInput!) {"
            " inventorySetQuantities(input: $input) { userErrors { field message } } }",
            {"input": {
                "name": "available",
                "reason": "correction",
                "ignoreCompareQuantity": True,
                "quantities": [{
                    "inventoryItemId": item.inventory_item_id,
                    "locationId": location_id,
                    "quantity": 0,
                }],
            }},
        )
