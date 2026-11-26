from decimal import Decimal as D
from nelly.purchases import Purchase, new_code, read_note, piece_costs


def test_codes_and_notes():
    assert new_code("2026-11-28", {"BUY-1128-1"}) == "BUY-1128-2"
    t = read_note("BUY-1128-1, 3 of 20")
    assert (t.invoice, t.lot, t.piece, t.of) == ("BUY-1128", "1", 3, 20)
    assert read_note("buy 1128 1").piece is None


def test_costs():
    p = Purchase("BUY-1128-1", "2026-11-28", "Smith estate", D("40"))
    c = piece_costs(p, [{"sku": "a", "price": 30}, {"sku": "b", "price": 10}])
    assert c == {"a": D("30.00"), "b": D("10.00")}
    p.total = None
    assert piece_costs(p, [{"sku": "a", "price": 30}]) == {"a": D("1.0")}
