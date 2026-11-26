from nelly.cards import CARDS, card_for, measurements_block, listing_photos


def test_all_cards_loaded():
    assert len(CARDS) == 43 and CARDS[0]["id"] == "J-01"


def test_picks_right_card():
    assert card_for("Vintage Avon Gold-Tone Bracelet With Pearl Accents")["id"] == "J-03"
    assert card_for("Sterling Silver Cuff Bracelet")["id"] == "J-04"
    assert card_for("Vintage Sterling Silver Manatee Pendant Charm")["id"] == "J-05"
    assert card_for("Harley-Davidson Leather Biker Trucker Wallet")["id"] == "A-05"
    assert card_for("Nautica Mens Silk Tie", ["menswear"]) is None


def test_measurement_text():
    c = card_for("bracelet")
    assert measurements_block(c, {"A": '7"', "B": ""}) == \
        'Measurements (approximate):\n• Length, end to end: 7"'
    assert measurements_block(c, {}) == ""


def test_bin_sheet_never_listed():
    assert listing_photos(["bin", "main", "x"], True) == ["main", "x"]
