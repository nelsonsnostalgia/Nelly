from decimal import Decimal as D
from nelly.markdown import start_price, times_marked, next_price


def test_start_and_count():
    assert start_price(24.5) == D("24.99") and start_price(25.1) == D("24.99")
    assert times_marked("29.99") == 0 and times_marked("27.97") == 2 and times_marked("30.00") == 0


def test_steps_down_to_half_off():
    p, seen = D("29.99"), []
    while True:
        new, _ = next_price(p, cost=1, original="29.99")
        if new is None:
            break
        seen.append(new)
        p = new
    assert seen[:3] == [D("27.98"), D("25.97"), D("23.96")]
    assert p >= D("15.00") and p < D("17.00")           # stops near 50% off


def test_dot_00_never_marked_down():
    new, why = next_price("45.00", cost=1)
    assert new is None and ".00" in why


def test_never_below_cost():
    assert next_price("9.99", cost=1)[0] == D("8.98")
    assert next_price("9.99", cost=9.5)[0] is None
