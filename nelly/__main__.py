"""Command line for NELLY.

  python -m nelly check            what settings are still missing
  python -m nelly ebay-link        print the eBay sign-in link
  python -m nelly ebay-code CODE   finish eBay sign-in (prints refresh token once)
  python -m nelly ebay-draft GID   make an unpublished eBay draft of one Shopify item
"""
import sys

from .config import Config
from .ebay import Ebay, consent_url, exchange_code
from .shopify import Shopify


def main(argv: list[str]) -> int:
    cfg = Config.from_env()
    cmd = argv[0] if argv else "check"
    if cmd == "check":
        missing = cfg.missing()
        print("Missing settings: " + ", ".join(missing) if missing else "All required settings found.")
        print("Publishing to eBay is " + ("ON" if cfg.publish_enabled else "OFF (drafts only)"))
        return 0
    if cmd == "ebay-link":
        print(consent_url(cfg))
        return 0
    if cmd == "ebay-code":
        tokens = exchange_code(cfg, argv[1])
        print("Save this as EBAY_REFRESH_TOKEN in the environment settings:")
        print(tokens["refresh_token"])
        return 0
    if cmd == "ebay-draft":
        item = Shopify(cfg).get_item(argv[1])
        ebay = Ebay(cfg)
        ebay.ensure_location("Sarasota", "FL", "34240")
        result = ebay.save_draft(item, ebay.policies())
        print(f"Draft saved on eBay (not live): {result}")
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
