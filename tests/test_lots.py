from decimal import Decimal as D
from nelly.lots import read_note, split, load, DEFAULT_CSV


def test_read_note():
    t = read_note("Bin 4  Neil's 50362-246, 1 of 3")
    assert (t.invoice, t.lot, t.piece, t.of) == ("50362", "246", 1, 3)
    assert t.label() == "Neil's 50362-246, 1 of 3"
    assert read_note("Neils 50362 - 246").piece is None
    assert read_note("yard sale, $2") is None


def test_split_by_price():
    c = split("7.08", [{"sku": "a", "price": 20}, {"sku": "b", "price": 10}, {"sku": "c", "price": 10}])
    assert c == {"a": D("3.54"), "b": D("1.77"), "c": D("1.77")}


def test_pennies_add_up():
    c = split("10.00", [{"sku": s, "price": 5} for s in "abc"])
    assert sum(c.values()) == D("10.00")


def test_sold_piece_keeps_cost():
    c = split("7.08", [{"sku": "a", "price": 20, "sold": True, "cost": "3.54"},
                       {"sku": "b", "price": 10}, {"sku": "c", "price": 10}, {"sku": "d", "price": 15}])
    assert c["a"] == D("3.54") and sum(c.values()) == D("7.08")


def test_real_lot():
    if DEFAULT_CSV.exists():
        assert load()[("50362", "246")].all_in == D("7.08")
