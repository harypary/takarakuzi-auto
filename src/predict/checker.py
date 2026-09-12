"""予想と当せん番号の照合"""

from src.config import Game

_LOTO_ORDER = ["1等", "2等", "3等", "4等", "5等", "6等"]
_NUMBERS_ORDER = ["ストレート", "ボックス", "ミニ相当"]


def _loto_prize(game: Game, matches: int, bonus: bool):
    if game.pick == 6:
        table = {6: "1等", 4: "4等", 3: "5等"}
        if matches == 5:
            return "2等" if bonus else "3等"
        return table.get(matches)
    if game.pick == 7:
        table = {7: "1等", 5: "4等", 4: "5等"}
        if matches == 6:
            return "2等" if bonus else "3等"
        if matches == 3 and bonus:
            return "6等"
        return table.get(matches)
    # ミニロト
    table = {5: "1等", 3: "4等"}
    if matches == 4:
        return "2等" if bonus else "3等"
    return table.get(matches)


def check_pick(game: Game, pick: dict, result: dict) -> dict:
    if game.kind == "loto":
        nums = set(pick["numbers"])
        matches = len(nums & set(result["main"]))
        bonus = bool(nums & set(result.get("bonus", [])))
        return {"matches": matches, "bonus": bonus, "prize": _loto_prize(game, matches, bonus)}

    mine, actual = pick["number"], result["number"]
    positions = sum(a == b for a, b in zip(mine, actual))
    if mine == actual:
        prize = "ストレート"
    elif sorted(mine) == sorted(actual) and len(set(actual)) > 1:
        prize = "ボックス"
    elif game.digits == 3 and mine[1:] == actual[1:]:
        prize = "ミニ相当"
    else:
        prize = None
    return {"positions": positions, "prize": prize}


def _rank(game: Game, ev: dict):
    order = _LOTO_ORDER if game.kind == "loto" else _NUMBERS_ORDER
    prize_rank = order.index(ev["prize"]) if ev["prize"] else len(order)
    return (prize_rank, -(ev.get("matches", 0) + ev.get("positions", 0)))


def evaluate(game: Game, picks: list, result: dict) -> dict:
    evals = [{**check_pick(game, p, result), "tier": p["tier"]} for p in picks]
    return {"evals": evals, "best": min(evals, key=lambda ev: _rank(game, ev))}
