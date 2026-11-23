# NELLY

Nelsons Nostalgia's own listing tool. Shopify is the master item list; NELLY
lists items on eBay (first), then Etsy, Whatnot and Facebook, and ends an item
everywhere when it sells anywhere.

## Safety rules built in

- eBay listings are saved as **drafts only** until `NELLY_PUBLISH=true`.
- Each item gets its own id `NN-<Shopify product number>`. The Shopify SKU
  field holds the shelf spot (for example `03 BIN 18`) and repeats, so it is
  kept as `shelf_spot`, not used as the id.
- Items without a known cost use `NELLY_DEFAULT_COGS` ($1.00).
- Listings already on eBay from List Perfectly are brought over with
  `migrate_listings`, never listed a second time.
- Markdowns never go below the item's price floor.

## Settings (environment variables, never in code)

| Name | What it is |
| --- | --- |
| `SHOPIFY_ADMIN_TOKEN` | Admin API token from the NELLY custom app in Shopify |
| `EBAY_CLIENT_ID` | eBay Production App ID |
| `EBAY_CLIENT_SECRET` | eBay Production Cert ID |
| `EBAY_RU_NAME` | eBay RuName for the sign-in link |
| `EBAY_REFRESH_TOKEN` | saved once after Diane signs in to eBay |
| `NELLY_PUBLISH` | `true` to let NELLY make listings live (default `false`) |

## Commands

```
python -m nelly check
python -m nelly ebay-link
python -m nelly ebay-code CODE
python -m nelly ebay-draft gid://shopify/Product/123
python -m pytest -q
```
