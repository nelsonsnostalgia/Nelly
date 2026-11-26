import pytest
from nelly.review import Review, REJECT_REASONS, sites_for


def test_approve_and_reject_flow():
    r = Review("NN-1", "Avon bracelet", 29.95, ["etsy"])
    r.reject(REJECT_REASONS[0], "clasp photo blurry")
    assert r.status == "rejected" and "blurry" in r.history[-1][2]
    r.resubmit()
    r.approve()
    assert r.status == "approved" and len(r.history) == 3
    with pytest.raises(ValueError):
        r.approve()


def test_reject_needs_reason():
    with pytest.raises(ValueError):
        Review("NN-2", "x", 1, []).reject("because")


def test_sites():
    assert sites_for("Vintage Avon", "", vintage=True, ebay_ready=False) == ["etsy", "shopify"]
    assert sites_for("New tie", "", vintage=False, ebay_ready=True) == ["ebay", "shopify"]
