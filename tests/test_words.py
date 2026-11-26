import pytest
from nelly import words
from nelly.etsy import listing_body
from nelly.config import Config
from nelly.shopify import item_from_node
from tests.test_core import NODE


def test_swaps_and_case():
    assert words.clean("Faux pearl, ivory lace, Amber glass") == \
        "Imitation pearl, off-white lace, Golden brown glass"


def test_hard_stop():
    with pytest.raises(words.BannedWordError):
        words.check("nice", "faux fur")
    words.check("imitation fur")


def test_listing_never_has_banned_words():
    node = {**NODE, "title": "Vintage Amber Glass Faux Pearl Ivory Brooch",
            "tags": ["faux pearl", "ivory"], "descriptionHtml": "<p>Faux amber</p>"}
    b = listing_body(item_from_node(node, 1.0), Config.from_env(), 1)
    words.check(b["title"], b["description"], b["tags"])
