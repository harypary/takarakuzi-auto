import random
from datetime import date, timedelta

import pytest

from src.config import DEFAULT_WEIGHTS, GAMES
from src.content.compliance import DISCLAIMER, find_ng
from src.koyomi import koyomi
from src.predict.checker import check_pick
from src.predict.engine import predict
from src.predict.learning import feature_performance, update_weights
from src.predict.engine import features_for


def _loto_results(game, count=300):
    rng = random.Random(1)
    start = date(2020, 1, 6)
    return [
        {"draw": i + 1, "date": (start + timedelta(days=3 * i)).isoformat(),
         "main": sorted(rng.sample(range(1, game.max_number + 1), game.pick)),
         "bonus": [n for n in rng.sample(range(1, game.max_number + 1), game.pick + game.bonus)][: game.bonus]}
        for i in range(count)
    ]


def _numbers_results(game, count=300):
    rng = random.Random(2)
    start = date(2020, 1, 6)
    return [
        {"draw": i + 1, "date": (start + timedelta(days=i)).isoformat(),
         "number": "".join(str(rng.randint(0, 9)) for _ in range(game.digits))}
        for i in range(count)
    ]


@pytest.mark.parametrize("key", ["loto6", "loto7", "miniloto"])
def test_loto_predictions_are_deterministic_and_valid(key):
    game = GAMES[key]
    results = _loto_results(game)
    ko = koyomi(date(2026, 9, 14))
    a = predict(game, results, ko, DEFAULT_WEIGHTS, 999)
    b = predict(game, results, ko, DEFAULT_WEIGHTS, 999)
    assert a["picks"] == b["picks"]
    assert len(a["picks"]) == 10
    combos = {tuple(p["numbers"]) for p in a["picks"]}
    assert len(combos) == 10
    c = a["constraints"]
    for p in a["picks"]:
        assert len(set(p["numbers"])) == game.pick
        assert c["sum_lo"] <= p["sum"] <= c["sum_hi"]


@pytest.mark.parametrize("key", ["numbers3", "numbers4"])
def test_numbers_predictions(key):
    game = GAMES[key]
    results = _numbers_results(game)
    pred = predict(game, results, koyomi(date(2026, 9, 14)), DEFAULT_WEIGHTS, 7000)
    numbers = [p["number"] for p in pred["picks"]]
    assert len(numbers) == 10 and len(set(numbers)) == 10
    assert all(len(n) == game.digits for n in numbers)


def test_loto6_prize_table():
    game = GAMES["loto6"]
    result = {"main": [1, 2, 3, 4, 5, 6], "bonus": [7]}
    assert check_pick(game, {"numbers": [1, 2, 3, 4, 5, 6]}, result)["prize"] == "1等"
    assert check_pick(game, {"numbers": [1, 2, 3, 4, 5, 7]}, result)["prize"] == "2等"
    assert check_pick(game, {"numbers": [1, 2, 3, 4, 5, 9]}, result)["prize"] == "3等"
    assert check_pick(game, {"numbers": [1, 2, 3, 10, 11, 12]}, result)["prize"] == "5等"
    assert check_pick(game, {"numbers": [1, 2, 10, 11, 12, 13]}, result)["prize"] is None


def test_numbers_prizes():
    n4, n3 = GAMES["numbers4"], GAMES["numbers3"]
    assert check_pick(n4, {"number": "1234"}, {"number": "1234"})["prize"] == "ストレート"
    assert check_pick(n4, {"number": "4321"}, {"number": "1234"})["prize"] == "ボックス"
    assert check_pick(n3, {"number": "923"}, {"number": "123"})["prize"] == "ミニ相当"


def test_weight_update_is_bounded_and_normalized():
    perf = {f: {"hits": 0, "baseline": 3.0} for f in DEFAULT_WEIGHTS}
    perf["hot"] = {"hits": 9, "baseline": 3.0}
    new = update_weights(DEFAULT_WEIGHTS, [perf] * 5)
    assert abs(sum(new.values()) - 1) < 1e-3
    assert new["hot"] > DEFAULT_WEIGHTS["hot"]
    assert all(0.049 <= v <= 0.401 for v in new.values())


def test_feature_performance_shapes():
    game = GAMES["loto6"]
    results = _loto_results(game)
    feats = features_for(game, results[:-1], koyomi(date(2026, 9, 14)))
    perf = feature_performance(game, feats, results[-1])
    assert set(perf) == set(DEFAULT_WEIGHTS)
    assert all(0 <= v["hits"] <= 6 for v in perf.values())


def test_compliance():
    assert find_ng("この予想は必ず当たる") == ["必ず当"]
    assert find_ng(DISCLAIMER) == []
