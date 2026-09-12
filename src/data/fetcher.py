"""当せん番号データの取得・正規化・保存

複数の公開CSVを順に取得し、回号ごとにマージして data/results/{game}.json に保存する。
CSVのヘッダー名から列を判定するので、提供元ごとの列順の違いを吸収できる。
"""

import csv
import io
import json
import re
import urllib.request
from datetime import date

from src.config import RESULTS_DIR, Game
from src.utils.logger import get_logger

logger = get_logger("fetcher")

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"


def _download(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def _decode(raw: bytes) -> str:
    for enc in ("utf-8-sig", "cp932"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")


def _parse_date(text: str) -> date:
    y, m, d = (int(x) for x in re.findall(r"\d+", text)[:3])
    return date(y, m, d)


def _find(header: list, pattern: str):
    return next((i for i, h in enumerate(header) if re.search(pattern, h, re.I)), None)


def parse_csv(game: Game, text: str) -> list:
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        return []
    header = [h.strip() for h in rows[0]]
    i_draw = _find(header, r"開催回|^No$|回号|回別")
    i_date = _find(header, r"日付|開催日|抽選日|抽せん日")
    if i_draw is None or i_date is None:
        raise ValueError(f"ヘッダーを解釈できません: {header[:6]}")

    if game.kind == "loto":
        mains = [i for i, h in enumerate(header) if re.fullmatch(r"(第\s*\d+\s*数字|本数字\s*\d+)", h)]
        bonuses = [i for i, h in enumerate(header) if re.search(r"BONUS|ボーナス", h, re.I)]
        i_co = _find(header, r"キャリーオーバー")
        if len(mains) < game.pick:
            raise ValueError(f"本数字の列が足りません: {header}")
    else:
        i_num = _find(header, r"抽選数字|当選数字|当せん番号|当選番号")
        if i_num is None:
            raise ValueError(f"当せん番号の列がありません: {header}")

    out = []
    for row in rows[1:]:
        try:
            rec = {"draw": int(re.sub(r"\D", "", row[i_draw])), "date": _parse_date(row[i_date]).isoformat()}
            if game.kind == "loto":
                main = sorted(int(row[i]) for i in mains[: game.pick])
                if len(set(main)) != game.pick or not all(1 <= n <= game.max_number for n in main):
                    continue
                rec["main"] = main
                rec["bonus"] = [int(row[i]) for i in bonuses[: game.bonus] if row[i].strip()]
                if i_co is not None and i_co < len(row):
                    rec["carryover"] = int(re.sub(r"\D", "", row[i_co]) or 0)
            else:
                number = re.sub(r"\D", "", row[i_num]).zfill(game.digits)
                if len(number) != game.digits:
                    continue
                rec["number"] = number
        except (ValueError, IndexError):
            continue
        out.append(rec)
    return out


def _results_path(game: Game):
    return RESULTS_DIR / f"{game.key}.json"


def load_results(game: Game) -> list:
    path = _results_path(game)
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def save_results(game: Game, results: list) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    # 1行1回にして git の差分を小さくする
    body = ",\n".join(json.dumps(r, ensure_ascii=False) for r in results)
    _results_path(game).write_text(f"[\n{body}\n]\n", encoding="utf-8")


def update_results(game: Game) -> list:
    """提供元から取得して保存し、回号順のリストを返す"""
    merged = {r["draw"]: r for r in load_results(game)}
    fresh = {}
    for url in game.sources:
        try:
            records = parse_csv(game, _decode(_download(url)))
            if len(records) < 100:
                raise ValueError(f"件数が少なすぎます（{len(records)}件）")
        except Exception as e:  # 提供元ごとの失敗は次の提供元で補う
            logger.warning(f"{game.name}: 取得失敗 {url}: {e}")
            continue
        logger.info(f"{game.name}: {url} から{len(records)}件（最新 第{records[-1]['draw']}回 {records[-1]['date']}）")
        for r in records:
            fresh.setdefault(r["draw"], r)

    if not fresh and not merged:
        raise RuntimeError(f"{game.name}: 当せん番号データを取得できませんでした")

    merged.update(fresh)
    results = sorted(merged.values(), key=lambda r: r["draw"])
    save_results(game, results)
    return results
