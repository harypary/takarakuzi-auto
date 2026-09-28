"""記事（タイトル・無料部分・有料部分・ハッシュタグ）の組み立て

note のエディタにはプレーンテキストで貼り付けるため、表は罫線と全角スペースで表現する。
データの一覧には必ず読み解きの文章を添え、数字の羅列だけにならないようにする。
"""

import json
from collections import Counter
from dataclasses import dataclass

from src.analysis.numbers import pattern_of
from src.config import DATA_DIR, FEATURE_LABELS, FEATURE_SHORT, FEATURES, MODEL_NAME, PICK_TIERS, Series
from src.content import commentary
from src.content.compliance import DISCLAIMER
from src.utils.dates import md_wd, ymd_ja

SEP = "━━━━━━━━━━━━━━━━━━"
CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩"


@dataclass
class Article:
    title: str
    teaser: str
    paid: str
    hashtags: list

    def to_markdown(self) -> str:
        return (
            f"# {self.title}\n\n{self.teaser}\n\n"
            "=============== ここから有料 ===============\n\n"
            f"{self.paid}\n\nハッシュタグ: {' '.join('#' + t for t in self.hashtags)}\n"
        )


def _h(title: str) -> str:
    return f"{SEP}\n■ {title}\n{SEP}"


def _n(n: int) -> str:
    return f"{n:02d}"


def _nums(ns) -> str:
    return " ".join(_n(n) for n in ns)


def _result(game, r: dict) -> str:
    if game.kind == "loto":
        bonus = f"（ボーナス {_nums(r['bonus'])}）" if r.get("bonus") else ""
        return _nums(r["main"]) + bonus
    return r["number"]


def _weights_line(weights: dict) -> str:
    return "／".join(f"{FEATURE_SHORT[f]} {weights[f] * 100:.1f}%" for f in FEATURES)


def _intro_link() -> list:
    """無料の紹介記事への導線（投稿済みの場合だけ入れる）"""
    path = DATA_DIR / "intro_post.json"
    if not path.exists():
        return []
    url = json.loads(path.read_text(encoding="utf-8")).get("url")
    if not url:
        return []
    return ["", "▼ このノートの読み方・6つの分析軸・毎週の検証のしかた（無料記事）", url]


def _koyomi_lines(ko: dict) -> list:
    lucky = "、".join(ko["lucky_days"]) or "特になし"
    return [
        f"・抽せん日：{ymd_ja(ko['date'])}",
        f"・六曜：{ko['rokuyo']}　九星（日盤）：{ko['kyusei_name']}　干支：{ko['kanshi']}",
        f"・節月：{ko['setsu_month_name']}　暦注の吉日：{lucky}",
        f"・五行：日の干＝{ko['day_gogyo']}／日の九星＝{ko['kyusei_gogyo']} → {ko['relation']}（{ko['relation_text']}）",
        f"・数秘（日付の数字の合計）：{ko['numerology']}",
        f"・暦のラッキーデジット：{' '.join(map(str, ko['lucky_digits']))}",
    ]


# ───────────────────────── 回顧・反映 ─────────────────────────

def _review_summary(game, rv: dict) -> str:
    tag = "【検証】" if rv["backtest"] else ""
    prizes = Counter(ev["prize"] for ev in rv["evals"] if ev["prize"])
    prize_text = "／当せん相当 " + "、".join(f"{k}×{v}" for k, v in prizes.items()) if prizes else "／当せん相当なし"
    best = rv["best"]
    if game.kind == "loto":
        return f"　→ {tag}10口中の最高一致 {best['matches']}個{prize_text}"
    return f"　→ {tag}10パターン中の最高 位置一致{best['positions']}桁{prize_text}"


def _mark(total: dict) -> str:
    hits, base = total["hits"], total["baseline"]
    if hits >= base * 1.2:
        return "▲上振れ"
    if hits <= base * 0.8:
        return "▼下振れ"
    return "―平均並み"


def _review_lines(ctx: dict, reviews: list) -> list:
    game = ctx["game"]
    out = []
    for rv in reviews:
        out.append(f"・第{rv['draw']}回 {md_wd(rv['date'])}　当せん番号 {_result(game, rv['result'])}")
        out.append(_review_summary(game, rv))
    return out


def _review_block(ctx: dict) -> list:
    game, wk = ctx["game"], ctx["weekly"]
    out = [f"【{game.name}】{md_wd(wk['review_start'])}〜{md_wd(wk['review_end'])}"]
    if not ctx["review_prev"]:
        out.append("・先週は対象の抽せんがありませんでした。")
        return out
    out += _review_lines(ctx, ctx["review_prev"])
    if wk["draws"]:
        unit = "個" if game.kind == "loto" else "桁"
        out.append("")
        if game.kind == "loto":
            out.append(f"＜分析軸ごとの成績＞各軸の上位{game.pick * 2}数字に当せん数字が何個入ったか")
        else:
            out.append("＜分析軸ごとの成績＞各桁で、各軸の上位3数字に当せん数字が入った桁数")
        for f in FEATURES:
            t = wk["totals"][f]
            out.append(f"・{FEATURE_LABELS[f]}：{t['hits']}{unit}（偶然なら{t['baseline']:.1f}{unit}）　{_mark(t)}")
    return out


def _reflection_block(ctx: dict) -> list:
    game, wk = ctx["game"], ctx["weekly"]
    out = [f"【{game.name}】分析軸の重み（合計100%）"]
    for f in FEATURES:
        before, after = wk["before"][f], wk["after"][f]
        arrow = "↑" if after - before > 0.004 else ("↓" if before - after > 0.004 else "→")
        out.append(f"・{FEATURE_LABELS[f]}：{before * 100:.1f}% → {after * 100:.1f}%　{arrow}")
    if not wk["draws"]:
        out.append("※先週の抽せんが無いため、重みは据え置きです。")
    return out


# ───────────────────────── 無料公開データ ─────────────────────────

def _free_data(ctx: dict) -> list:
    game, a = ctx["game"], ctx["analysis"]
    if game.kind == "loto":
        verdict = "0.05以上＝統計的に目立つ偏りなし" if a["chi_p"] >= 0.05 else "0.05未満＝偏りあり"
        return [
            f"・{game.name} 全{a['total']:,}回の数字ごとの出現回数の偏り：カイ二乗検定 p値 {a['chi_p']:.2f}（{verdict}）",
            f"・合計値の中心帯（全回の80%）：{a['sum_lo']}〜{a['sum_hi']}（平均 {a['sum_mean']:.1f}）",
            f"・前回からの引っ張り：全回平均 {a['carry_mean']:.2f}個",
            f"・連番を含む回の割合：全回 {a['consec_all']:.0%}／直近20回 {a['consec_20']:.0%}",
        ]
    patterns = "／".join(f"{k} {v:.0%}" for k, v in a["pattern_all"])
    return [
        f"・{game.name} 全{a['total']:,}回のパターン比率：{patterns}",
        f"・数字合計の中心帯（全回の80%）：{a['sum_lo']}〜{a['sum_hi']}（平均 {a['sum_mean']:.1f}）",
    ]


def _contents(series: Series) -> list:
    if series.key == "numbers":
        return [
            "【有料部分の内容】",
            "・暦分析：六曜・九星・干支・吉日・五行・数秘の由来と、今回の数字選びへの読み解き",
            "・ナンバーズ4／3 データ分析① 桁別の出現傾向（よく出る数字・沈黙している数字）",
            "・データ分析② パターン比率・数字合計・直近の流れ・偏り検定",
            "・データ×暦の桁別統合スコアと各桁の軸数字",
            "・ナンバーズ4 予想10パターン／ナンバーズ3 予想10パターン（本命・対抗・穴、各パターンの性格と買い方の目安つき）",
            "・おわりに　暦からのひとこと",
        ]
    return [
        "【有料部分の内容】",
        "・暦分析：六曜・九星・干支・吉日・五行・数秘の由来と、今回の数字選びへの読み解き",
        "・データ分析① 出現頻度ランキング（直近20回・100回・全回、z値つき）と読み解き",
        "・データ分析② インターバル（未出現期間）ランキングと読み解き",
        "・データ分析③ 引っ張り・スライド・合計値・奇数偶数・小さい数字・連番",
        "・データ分析④ よく一緒に出る“相性のいいコンビ”",
        "・暦数字と、データ×暦の統合スコア（軸数字・除外候補）",
        "・予想10口（本命4・対抗3・穴3）と、1口ずつの性格",
        "・おわりに　暦からのひとこと",
    ]


# ───────────────────────── 有料部分 ─────────────────────────

def _paid_loto(ctx: dict) -> list:
    game, a, p = ctx["game"], ctx["analysis"], ctx["pred"]
    L = [_h(f"{game.name} データ分析① 出現頻度ランキング")]
    L.append(f"まずは「最近よく出ている数字」から。直近20回で1つの数字が出る期待値は{a['e20']:.1f}回、直近100回なら{a['e100']:.1f}回です（z値は±2を超えると偏りが大きい目安）。")
    for i, n in enumerate(a["hot"], 1):
        L.append(f"{i:>2}位　{_n(n)}　直近20回 {a['f20'][n]}回／直近100回 {a['f100'][n]}回（z {a['z100'][n]:+.2f}）／全回 {a['fall'][n]}回")
    L += ["", commentary.loto_hot_comment(ctx)]

    L += ["", _h(f"{game.name} データ分析② インターバル（未出現期間）")]
    L.append(f"続いては、しばらく姿を見せていない数字です。1つの数字が出る平均的な間隔は約{a['mean_gap']:.1f}回です。")
    for i, n in enumerate(a["cold"], 1):
        L.append(f"{i:>2}位　{_n(n)}　{a['interval'][n]}回連続で未出現")
    L += ["", commentary.loto_cold_comment(ctx)]

    last = a["last"]
    L += ["", _h(f"{game.name} データ分析③ 出目の形")]
    L.append("数字そのものではなく、当せん番号の“形”にも注目してみましょう。")
    L.append(f"・前回 第{last['draw']}回：{_result(game, last)}")
    cd = a["carry_dist"]
    L.append(f"・引っ張り（前回と同じ数字）：全回平均 {a['carry_mean']:.2f}個（0個 {cd[0]:.0%}／1個 {cd[1]:.0%}／2個以上 {cd[2]:.0%}）")
    L.append(f"・スライド（前回数字の±1）：全回平均 {a['slide_mean']:.2f}個")
    L.append(f"・合計値：全回平均 {a['sum_mean']:.1f}（標準偏差 {a['sum_std']:.1f}）、80%帯 {a['sum_lo']}〜{a['sum_hi']}")
    L.append(f"　直近10回の合計値：{' → '.join(map(str, a['recent_sums']))}")
    odd_all = "／".join(f"{c}個 {s:.0%}" for c, s in a["odd_top_all"])
    odd_20 = "／".join(f"{c}個 {s:.0%}" for c, s in a["odd_top_20"])
    L.append(f"・奇数の個数（多い順）：全回 {odd_all}　直近20回 {odd_20}")
    L.append(f"・小さい数字（1〜{a['low_max']}）の個数：全回平均 {a['low_mean']:.2f}個／直近20回平均 {a['low_mean_20']:.2f}個")
    L.append(f"・連番を含む回：全回 {a['consec_all']:.0%}／直近20回 {a['consec_20']:.0%}")
    L.append(f"・出現回数の偏り（全回）：カイ二乗 {a['chi2']:.1f}（自由度{game.max_number - 1}）、p値 {a['chi_p']:.2f}")
    L += ["", commentary.loto_shape_comment(ctx)]

    L += ["", _h(f"{game.name} データ分析④ 相性のいいコンビ（直近100回）")]
    for (x, y), c in a["top_pairs"]:
        L.append(f"・{_n(x)} と {_n(y)}：{c}回")
    L += ["", commentary.loto_pair_comment(ctx)]

    L += ["", _h(f"{game.name} 暦数字")]
    L.append("暦のラッキーデジット・九星・数秘・日付と重なる数字を、暦スコアの高い順に選びました。データとはまったく別の角度から見た、今回の“ご縁のある数字”です。")
    L.append(f"・暦数字：{_nums(p['koyomi_numbers'])}")

    L += ["", _h(f"{game.name} 統合スコア（データ×暦）")]
    L.append("ここまでのデータと暦を一つにまとめます。数字ごとに6つの分析軸のスコア（0〜1）を出し、今週の重みを掛けて合計しました。")
    L.append(f"今週の重み：{_weights_line(p['weights'])}")
    for i, row in enumerate(p["top"], 1):
        parts = " ".join(f"{FEATURE_SHORT[f]}{row['parts'][f]:.2f}" for f in FEATURES)
        L.append(f"{i:>2}位　{_n(row['n'])}　総合 {row['total']:.3f}（{parts}）")
    L.append(f"◎軸数字：{_nums(p['axis'])}　×除外候補：{_nums(p['exclude'])}")
    L += ["", commentary.loto_score_comment(ctx)]

    L += ["", _h(f"{game.name} 第{ctx['draw']}回 予想10口（{md_wd(ctx['date'])}抽せん）")]
    L.append("いよいよ今回の10口です。本命・対抗・穴は、それぞれ違う物差しで選んでいます。1口ずつの“性格”も添えたので、ご自身の直感に合うものを選ぶ参考にしてください。")
    used_tags = {}
    for tier, _ in PICK_TIERS:
        L += ["", f"【{tier}】", commentary.TIER_INTRO[tier]]
        for i, pk in enumerate(x for x in p["picks"] if x["tier"] == tier):
            axis_n = len(set(pk["numbers"]) & set(p["axis"]))
            ko_n = len(set(pk["numbers"]) & set(p["koyomi_numbers"]))
            L.append(f"{tier}{CIRCLED[i]}　{_nums(pk['numbers'])}　（合計{pk['sum']}／奇数{pk['odd']}個／軸{axis_n}個／暦数字{ko_n}個）")
            L.append(f"　└ {commentary.choose_tag(commentary.loto_pick_tags(pk, ctx), used_tags)}")
    c = p["constraints"]
    L.append("")
    L.append(
        f"※絞り込み条件：合計値{c['sum_lo']}〜{c['sum_hi']}、奇数{'・'.join(map(str, c['odd_allowed']))}個、"
        f"3連番以上なし、引っ張り2個以内、10口どうしの共通数字は原則{c['max_shared']}個以内、1つの数字の登場は原則5口まで"
    )
    L.append("")
    return L


def _paid_numbers(ctx: dict) -> list:
    game, a, p = ctx["game"], ctx["analysis"], ctx["pred"]
    L = [_h(f"{game.name} データ分析① 桁別の出現傾向")]
    L.append("ナンバーズは桁ごとに数字が決まります。直近30回の出現回数（1つの数字あたりの期待値は3回）と、何回連続で出ていないかを桁ごとに整理しました。")
    for pos in a["positions"]:
        hot = "  ".join(f"{g}（{pos['f30'][g]}回）" for g in pos["hot"])
        cold = "  ".join(f"{g}（{pos['interval'][g]}回未出現）" for g in pos["cold"])
        L.append(f"・{pos['label']}　よく出る：{hot}")
        L.append(f"　　　　　出ていない：{cold}")
    L += ["", commentary.numbers_position_comment(ctx)]

    last = a["last"]
    L += ["", _h(f"{game.name} データ分析② 出目の形")]
    L.append(f"・前回 第{last['draw']}回：{last['number']}（{pattern_of(last['number'])}）")
    L.append("・直近10回：" + " → ".join(num for _, num in a["recent"]))
    L.append("・パターン比率　全回：" + "／".join(f"{k} {v:.0%}" for k, v in a["pattern_all"]))
    L.append("　　　　　　　直近30回：" + "／".join(f"{k} {v:.0%}" for k, v in a["pattern_30"]))
    L.append(f"・数字合計：全回平均 {a['sum_mean']:.1f}、80%帯 {a['sum_lo']}〜{a['sum_hi']}、直近10回 {' → '.join(map(str, a['recent_sums']))}")
    L.append(f"・前回と同じ桁に同じ数字が出た回：全回の{a['repeat_rate']:.0%}")
    L.append("・直近30回で出現が多い数字（全桁合計）：" + "  ".join(f"{g}（{c}回）" for g, c in a["digits_30"]))
    if a["missing_30"]:
        L.append("・直近30回でどの桁にも出ていない数字：" + " ".join(map(str, a["missing_30"])))
    L.append("・桁ごとの偏り検定（全回・カイ二乗 p値）：" + "／".join(f"{pos['label']} {pos['chi_p']:.2f}" for pos in a["positions"]))
    L += ["", commentary.numbers_shape_comment(ctx)]

    L += ["", _h(f"{game.name} 統合スコア（データ×暦）")]
    L.append("桁ごとに6つの分析軸のスコアを出し、今週の重みを掛けて合計しました。各桁の上位3つです。")
    L.append(f"今週の重み：{_weights_line(p['weights'])}")
    for pos, rows in zip(a["positions"], p["top"]):
        L.append(f"・{pos['label']}：" + "  ".join(f"{r['g']}（{r['total']:.2f}）" for r in rows))
    L.append("◎各桁の軸数字：" + "／".join(f"{pos['label']} {' '.join(map(str, axis))}" for pos, axis in zip(a["positions"], p["axis"])))
    L += ["", commentary.numbers_score_comment(ctx)]

    L += ["", _h(f"{game.name} 第{ctx['draw']}回 予想10パターン（{md_wd(ctx['date'])}抽せん）")]
    L.append("本命・対抗・穴は、それぞれ違う物差しで選んでいます。各パターンの“性格”と買い方の目安も添えました。")
    used_tags = {}
    for tier, _ in PICK_TIERS:
        L += ["", f"【{tier}】", commentary.TIER_INTRO[tier]]
        for i, pk in enumerate(x for x in p["picks"] if x["tier"] == tier):
            L.append(f"{tier}{CIRCLED[i]}　{pk['number']}　（{pk['pattern']}／合計{pk['sum']}／買い方の目安：{pk['buy']}）")
            L.append(f"　└ {commentary.choose_tag(commentary.numbers_pick_tags(pk, ctx), used_tags)}")
    L.append("")
    L.append(f"※10パターンどうしで同じ桁に同じ数字が並ぶのは原則{p['max_shared']}桁以内、同じ数字の並べ替え（同じボックス）は1つだけに制限しています。")
    L.append("")
    return L


# ───────────────────────── 組み立て ─────────────────────────

def build_title(series: Series, ctxs: list) -> str:
    c = ctxs[0]
    md = md_wd(c["date"])
    if series.key == "numbers":
        return f"【ナンバーズ3・4予想】第{c['draw']}回 {md}｜データ分析×暦で導く各10パターン【{MODEL_NAME}】"
    carryover = c["last"].get("carryover") or 0
    tail = f"｜キャリーオーバー約{carryover / 1e8:.1f}億円" if carryover >= 1e8 else ""
    return f"【{series.title_name}予想】第{c['draw']}回 {md}｜データ分析×暦で導く厳選10口【{MODEL_NAME}】{tail}"


def build_teaser(series: Series, ctxs: list, narr: dict) -> str:
    ko = ctxs[0]["ko"]
    P = [narr["hook"], "", _h("対象回と抽せん日の暦")]
    for x in ctxs:
        P.append(f"・{x['game'].name} 第{x['draw']}回（{ymd_ja(x['date'])}抽せん）")
    P += _koyomi_lines(ko)[1:3]
    P += ["", commentary.koyomi_teaser(ko)]

    P += ["", _h("先週の回顧")]
    P.append("まずは先週の答え合わせから。予想した数字と実際の当せん番号を並べ、どの分析軸がうまく機能したのかを確認します。")
    P.append("")
    for x in ctxs:
        P += _review_block(x) + [""]
    P.append(narr["review"])

    P += ["", _h("今週の予想への反映")]
    P.append("先週の結果を受けて、今週は6つの分析軸のバランスを次のように調整しました。")
    P.append("")
    for x in ctxs:
        P += _reflection_block(x) + [""]
    P.append(narr["reflection"])

    current = []
    for x in ctxs:
        if x["review_cur"]:
            current += [f"【{x['game'].name}】"] + _review_lines(x, x["review_cur"])
    if current:
        P += ["", _h("今週これまでの結果")] + current

    P += ["", _h("無料公開データ（抜粋）")]
    for x in ctxs:
        P += _free_data(x) + ["", commentary.free_data_comment(x), ""]

    P += [_h("有料部分の見どころ"), commentary.paid_highlight(series.key, ctxs), ""]
    P += _contents(series)
    P += _intro_link()
    P += ["", DISCLAIMER]
    return "\n".join(P)


def build_paid(series: Series, ctxs: list, narr: dict) -> str:
    P = [_h("暦分析 抽せん日の暦を読む")] + _koyomi_lines(ctxs[0]["ko"]) + ["", narr["koyomi"], ""]
    for x in ctxs:
        P += _paid_loto(x) if x["game"].kind == "loto" else _paid_numbers(x)
    P += [_h("おわりに　暦からのひとこと"), narr["message"], "", DISCLAIMER]
    return "\n".join(P)


def build_article(series: Series, ctxs: list, narr: dict) -> Article:
    return Article(
        title=build_title(series, ctxs),
        teaser=build_teaser(series, ctxs, narr),
        paid=build_paid(series, ctxs, narr),
        hashtags=list(series.hashtags),
    )
