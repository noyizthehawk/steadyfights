"""Ask Bout Brain: the precomputed head-to-head and the daily allowance.
No model calls; the Claude call itself is checked by hand."""
import pytest

from web.backend import bout_qa


def _d(name, **kw):
    base = {
        "name": name,
        "physical": {"height_cm": 180.0, "reach_cm": 180.0, "age": 30.0},
        "striking": {}, "durability": {}, "grappling": {}, "ratings_0_to_100": {},
    }
    for path, v in kw.items():
        sec, key = path.split("__")
        base[sec][key] = v
    return base


def line(lines, label):
    return next(l for l in lines if l.startswith(label + ":"))


def test_reach_goes_to_the_longer_one():
    # the bug this exists for: Haiku once gave reach to the shorter fighter
    lines = bout_qa.head_to_head(_d("A", physical__reach_cm=177.8), _d("B", physical__reach_cm=188.0))
    assert line(lines, "Reach").endswith("Longer reach: B.")


def test_lower_is_better_stats():
    lines = bout_qa.head_to_head(
        _d("A", striking__sig_strikes_absorbed_per_min=1.4, durability__times_knocked_down=0),
        _d("B", striking__sig_strikes_absorbed_per_min=2.6, durability__times_knocked_down=3),
    )
    assert line(lines, "Significant strikes absorbed per minute").endswith("Better: A.")
    assert line(lines, "Times knocked down in the UFC").endswith("Better: A.")


def test_younger_and_level_and_missing():
    lines = bout_qa.head_to_head(
        _d("A", physical__age=35.0, grappling__takedowns_per_15min=1.0),
        _d("B", physical__age=29.0, grappling__takedowns_per_15min=1.0),
    )
    assert line(lines, "Age").endswith("Younger: B.")
    assert line(lines, "Takedowns landed per 15 min").endswith("Level.")
    assert "no data" in line(lines, "Career score")


def test_height_shows_feet_and_inches():
    lines = bout_qa.head_to_head(_d("A", physical__height_cm=177.8), _d("B", physical__height_cm=190.5))
    assert "5'10\"" in line(lines, "Height") and "6'3\"" in line(lines, "Height")


class FakeRedis:
    def __init__(self):
        self.d = {}

    def incr(self, k):
        self.d[k] = int(self.d.get(k, 0)) + 1
        return self.d[k]

    def expire(self, *a):
        pass

    def get(self, k):
        return self.d.get(k)


def test_free_allowance_then_paywall(monkeypatch):
    monkeypatch.setattr(bout_qa, "redis_client", FakeRedis())
    left = [bout_qa._spend(1, subscribed=False) for _ in range(bout_qa.FREE_DAILY)]
    assert left == list(range(bout_qa.FREE_DAILY - 1, -1, -1))
    with pytest.raises(bout_qa.AskError) as e:
        bout_qa._spend(1, subscribed=False)
    assert e.value.status == 402
    assert bout_qa.remaining(1, subscribed=False) == 0


def test_subscriber_gets_more_and_429_not_402(monkeypatch):
    monkeypatch.setattr(bout_qa, "redis_client", FakeRedis())
    for _ in range(bout_qa.SUB_DAILY):
        bout_qa._spend(2, subscribed=True)
    with pytest.raises(bout_qa.AskError) as e:
        bout_qa._spend(2, subscribed=True)
    assert e.value.status == 429


def test_question_validation_before_any_spend(monkeypatch):
    r = FakeRedis()
    monkeypatch.setattr(bout_qa, "redis_client", r)
    for q in ("", "   ", "x" * 201):
        with pytest.raises(bout_qa.AskError) as e:
            bout_qa.ask("A", "B", q, 3, False)
        assert e.value.status == 400
    assert r.d == {}   # nothing charged


def test_cache_key_ignores_case_and_punctuation():
    assert bout_qa._cache_key("A", "B", "Who's taller?") == bout_qa._cache_key("A", "B", "  whos TALLER ")
    assert bout_qa._cache_key("A", "B", "x") != bout_qa._cache_key("B", "A", "x")


def test_resolve_matches_event_card_spellings(monkeypatch):
    monkeypatch.setattr(bout_qa.model, "list_fighters", lambda: ["Roberto Soldic", "Benoit Saint Denis"], raising=False)
    bout_qa._name_index.cache_clear()
    try:
        assert bout_qa.resolve("Roberto Soldić") == "Roberto Soldic"
        assert bout_qa.resolve("  benoît  saint denis ") == "Benoit Saint Denis"
        assert bout_qa.resolve("Some Debutant") is None
    finally:
        bout_qa._name_index.cache_clear()


def test_counts_down_without_redis(monkeypatch):
    # local dev has no Redis; the allowance used to silently stop counting
    monkeypatch.setattr(bout_qa, "redis_client", None)
    monkeypatch.setattr(bout_qa, "_mem_counts", {})
    assert bout_qa.remaining(9, subscribed=False) == bout_qa.FREE_DAILY
    assert bout_qa._spend(9, subscribed=False) == bout_qa.FREE_DAILY - 1
    assert bout_qa.remaining(9, subscribed=False) == bout_qa.FREE_DAILY - 1
