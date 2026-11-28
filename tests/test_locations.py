from nelly.locations import parse


def test_parse():
    assert parse("03 BIN 18").say() == "Shelf 3, Bin 18"
    t = parse("5 tray 1")
    assert t.code() == "05 TRAY 01" and t.say() == "Shelf 5, Red Tray 1"
    assert parse("F00191") is None
