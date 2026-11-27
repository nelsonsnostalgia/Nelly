from decimal import Decimal as D
from nelly.markdown import start_price, times_marked, next_price


def test_start_and_count():
    assert start_price(24.5) == D("24.99") and start_price(25.1) == D("24.99")
    assert times_marked("29.99") == 0 and times_marked("27.97") == 2 and times_marked("30.00") == 0


def test_steps_down_one_cent_each_time():
    p, seen = D("29.99"), []
    for _ in range(5):
        p, _why = next_price(p, cost=1)
        seen.append(p)
    assert seen == [D("27.98"), D("25.97"), D("23.96"), D("21.95"), D("19.94")]
    assert next_price(p, cost=1)[0] is None          # stops after 5


def test_at_least_5_percent_and_floor():
    new, _ = next_price("9.99", cost=1)
    assert new == D("8.98")                           # cheap item: about 10%
    assert next_price("5.99", cost=1)[0] is None      # $5 floor
    assert next_price("49.99", cost=24)[0] is None    # 2x cost = $48 floor
