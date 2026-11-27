from datetime import datetime, timedelta
from nelly.takedown import Queue, double_sale

T0 = datetime(2026, 11, 27, 9, 0)


def test_sold_removes_everywhere_else(tmp_path):
    q = Queue(tmp_path / "q.json")
    jobs = q.add("NN-1", "etsy", ["ebay", "etsy", "shopify"], T0)
    assert {j.site for j in jobs} == {"ebay", "shopify"}
    gone = set()
    alerts = q.run(T0, lambda s, k: gone.add(s), lambda s, k: s not in gone)
    assert alerts == [] and q.open_jobs() == []


def test_glitch_retries_alerts_and_remembers(tmp_path):
    p = tmp_path / "q.json"
    q = Queue(p)
    q.add("NN-2", "ebay", ["etsy"], T0)
    def broken(s, k):
        raise TimeoutError("Etsy down")
    t, alerts = T0, []
    for _ in range(4):                       # 5m, 15m, 1h waits
        alerts += q.run(t, broken, lambda s, k: True)
        t = datetime.fromisoformat(q.open_jobs()[0].next_try)
    assert any("STILL LIVE" in a for a in alerts)
    q2 = Queue(p)                            # NELLY restarted: job is still there
    assert q2.open_jobs()[0].status == "stuck"
    q2.run(t + timedelta(days=2), lambda s, k: None, lambda s, k: False)
    assert q2.open_jobs() == []


def test_removed_but_still_live_is_not_done(tmp_path):
    q = Queue(tmp_path / "q.json")
    q.add("NN-3", "ebay", ["etsy"], T0)
    q.run(T0, lambda s, k: None, lambda s, k: True)
    assert q.open_jobs()[0].tries == 1


def test_morning_sweep_requeues(tmp_path):
    q = Queue(tmp_path / "q.json")
    found = q.daily_sweep({"NN-4": "ebay"}, {"NN-4": ["ebay", "etsy"]}, lambda s, k: True, T0)
    assert found == ["NN-4 still live on etsy"] and q.open_jobs()[0].site == "etsy"


def test_double_sale_alert():
    assert double_sale([("A", "ebay"), ("A", "etsy")])
    assert not double_sale([("A", "ebay"), ("A", "ebay")])
