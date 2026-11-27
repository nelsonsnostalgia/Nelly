from datetime import date, timedelta
from nelly.relist import Live, pick, plan, record

T = date(2026, 11, 27)


def L(sku, site="ebay", days=90, price=20, **kw):
    return Live(sku, sku, site, "id-" + sku, price, T - timedelta(days=days), **kw)


def test_oldest_first_and_limit():
    items = [L(f"s{i}", days=60 + i) for i in range(15)]
    go, _ = pick(items, T)
    assert len(go) == 10 and go[0].sku == "s14"


def test_too_new_skipped_and_etsy_sooner():
    go, _ = pick([L("new", days=10), L("etsy", site="etsy", days=31)], T)
    assert [x.sku for x in go] == ["etsy"]


def test_rare_with_watchers_held():
    trumpet = L("trumpet", price=450, watchers=1)
    go, held = pick([trumpet, L("plain", watchers=1)], T)
    assert [x.sku for x in go] == ["plain"] and held[0][0].sku == "trumpet"
    assert "offer" in held[0][1]


def test_protect_and_chats():
    _, held = pick([L("a", protected=True), L("b", open_chats=1)], T)
    assert {x.sku for x, _ in held} == {"a", "b"}


def test_history_resets_clock():
    x = L("a", days=200)
    record(x, T, "id-new")
    assert x.listing_id == "id-new" and pick([x], T)[0] == []
    assert plan([L("e", site="etsy", days=40)], T)[0]["do"] == "renew"


def test_relist_marks_down():
    r = plan([L("a", price=29.99, cost=1)], T)[0]
    assert r["new_price"] == 27.98 and not r["decide"]
    r = plan([L("b", price=15.88, cost=1, original=29.99)], T)[0]
    assert r["new_price"] == 15.88 and r["decide"]          # 50% off limit
    r = plan([L("c", price=45.00, cost=1)], T)[0]
    assert r["new_price"] == 45.00 and not r["decide"]      # Eric's .00 = no markdown
