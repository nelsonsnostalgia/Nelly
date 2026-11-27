from datetime import date, timedelta
from nelly.seasons import season_for, window, in_season
from nelly.relist import Live, pick, plan


def test_tagging():
    assert season_for("Vintage Santa Claus Mug") == "Christmas"
    assert season_for("Blow Mold Pumpkin") == "Halloween"
    assert season_for("Avon bracelet") is None
    assert season_for("Glass bird", ["ornament"]) == "Christmas"


def test_windows():
    assert window("Christmas", date(2027, 1, 15)) == (date(2027, 10, 1), date(2027, 12, 20))
    assert in_season("Winter", date(2027, 1, 10)) and not in_season("Christmas", date(2027, 1, 10))


def item(day_listed, season="Christmas", price=39.99):
    return Live("x", "Santa mug", "ebay", "id", price, day_listed, season=season, cost=1)


def test_held_out_of_season():
    go, held = pick([item(date(2026, 1, 5))], date(2027, 3, 1))
    assert go == [] and "Saving for Christmas" in held[0][1]


def test_pushed_first_when_season_opens_no_markdown():
    today = date(2027, 10, 2)
    everyday = Live("old", "Old lamp", "ebay", "id2", 50, today - timedelta(days=300))
    xmas = item(today - timedelta(days=20))          # young, but season just opened
    go, _ = pick([everyday, xmas], today)
    assert [g.sku for g in go] == ["x", "old"]
    row = plan([xmas], today)[0]
    assert row["new_price"] == 39.99 and not row["decide"]


def test_after_season_markdown_once():
    from nelly.relist import season_markdowns
    x = item(date(2026, 11, 1), price=39.99)
    assert season_markdowns([x], date(2026, 12, 10)) == []          # still in season
    r = season_markdowns([x], date(2026, 12, 21))[0]
    assert r["new_price"] == 31.98                                    # 20% off, cents .98
    x.price, x.season_marked = 31.98, date(2026, 12, 21)
    assert season_markdowns([x], date(2027, 6, 1)) == []              # holds all year
    late = item(date(2027, 1, 5))                                     # listed after Christmas
    assert season_markdowns([late], date(2027, 6, 1)) == []
