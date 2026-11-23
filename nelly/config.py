"""Settings for NELLY, read from environment variables.

Secrets (keys, tokens) are never written in code or files. They come from the
hosting environment's settings.
"""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    # Shopify (master item list)
    shopify_store: str          # e.g. hmtpyx-au.myshopify.com
    shopify_token: str          # Admin API access token from the NELLY custom app
    shopify_api_version: str

    # eBay
    ebay_client_id: str
    ebay_client_secret: str
    ebay_ru_name: str           # eBay "RuName" (redirect name) for the sign-in link
    ebay_refresh_token: str     # saved after Diane signs in once
    ebay_marketplace: str
    ebay_location_key: str      # NELLY's ship-from location on eBay

    # House rules
    default_cogs: float         # cost used when an item has no known cost
    publish_enabled: bool       # False = make eBay drafts only, never go live

    @staticmethod
    def from_env() -> "Config":
        e = os.environ.get
        return Config(
            shopify_store=e("SHOPIFY_STORE", "hmtpyx-au.myshopify.com"),
            shopify_token=e("SHOPIFY_ADMIN_TOKEN", ""),
            shopify_api_version=e("SHOPIFY_API_VERSION", "2026-10"),
            ebay_client_id=e("EBAY_CLIENT_ID", ""),
            ebay_client_secret=e("EBAY_CLIENT_SECRET", ""),
            ebay_ru_name=e("EBAY_RU_NAME", ""),
            ebay_refresh_token=e("EBAY_REFRESH_TOKEN", ""),
            ebay_marketplace=e("EBAY_MARKETPLACE", "EBAY_US"),
            ebay_location_key=e("EBAY_LOCATION_KEY", "nelly-sarasota"),
            default_cogs=float(e("NELLY_DEFAULT_COGS", "1.00")),
            publish_enabled=e("NELLY_PUBLISH", "false").lower() == "true",
        )

    def missing(self) -> list[str]:
        """Names of required settings that are not filled in yet."""
        need = {
            "SHOPIFY_ADMIN_TOKEN": self.shopify_token,
            "EBAY_CLIENT_ID": self.ebay_client_id,
            "EBAY_CLIENT_SECRET": self.ebay_client_secret,
        }
        return [k for k, v in need.items() if not v]
