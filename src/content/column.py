"""無料コラム（週1回）の組み立て

同じ記事の使い回しにならないよう、4種類を持ち回りにする。どれも実データから毎回作り直す。
  myths   よくある誤解をデータで確かめる
  report  直近1か月の出目レポート
  koyomi  これからの暦カレンダー（吉日と抽せん日）

※ 当せん実績の掲載は購入を煽る表現と受け取られうるため、成績の公開は各予想記事の
   「先週の回顧」に限っている（コラムでは扱わない）。
"""

from datetime import date, timedelta

from src.config import GAMES, MODEL_NAME, SERIES
from src.content.article import _h, _intro_link
from src.content.commentary import LUCKY_DETAIL, SEASON
from src.content.compliance import DISCLAIMER
from src.koyomi import koyomi
from src.utils.dates import is_draw_day, md_wd, to_date, ymd_ja

TOPICS = ("myths", "report", "koyomi")
COOLDOWN_DAYS = 21

BASE_HASHTAGS = ["宝くじ", "宝くじ予想", "データ分析", "数字選択式宝くじ", "note"]


def choose_topic(today: date, history: list) -> str:
    """直近 COOLDOWN_DAYS に使っていない種類を選ぶ（なければ最も古いもの）"""
    last_used = {}
    for post in history:
        if post.get("topic"):
            last_used[post["topic"]] = max(last_used.get(post["topic"], ""), post.get("posted_at", ""))
    for topic in TOPICS:
        used = last_used.get(topic)
        if not used:
            return topic
        if (today - to_date(used[:10])).days > COOLDOWN_DAYS:
            return topic
    return min(TOPICS, key=lambda t: last_used.get(t, ""))


def _lineup_lines() -> list:
    lines = []
    for key in ("numbers", "loto6", "loto7"):
        s = SERIES[key]
        lines.append(f"・{s.title_name}予想（{s.price}円）")
    return lines


def _closing(P: list) -> list:
    P += ["", _h("このノートについて"),
          "ロト6・ロト7・ナンバーズ3・4の予想を、過去の全データの統計と抽せん日の暦の両面から組み立てて公開しています。"
          "毎週、先週の予想を結果と照らし合わせて検証し、その結果を次の予想の重みに反映しています。外れた回も隠しません。"]
    P += _lineup_lines()
    P += _intro_link()
    P += ["", DISCLAIMER]
    return P


# ───────────────────────── 1. よくある誤解 ─────────────────────────

def build_myths(ctx: dict) -> tuple:
    loto, numbers = ctx["loto"], ctx["numbers"]
    l6, l7 = loto["loto6"], loto["loto7"]
    n4, n3 = numbers["numbers4"], numbers["numbers3"]
    total_all = l6["total"] + l7["total"] + n4["total"] + n3["total"]
    title = f"ロト・ナンバーズの「よくある誤解」を全{total_all:,}回のデータで確かめてみた【無料・{MODEL_NAME}】"

    P = [
        "「連番は出にくい」「同じ数字が続けて出ることはない」「よく出る数字がある」――。"
        "宝くじの数字選びには、いろいろな言い伝えがあります。",
        "",
        f"この記事では、ロト6・ロト7・ナンバーズ3・4の全{total_all:,}回ぶんの当せん番号を使って、"
        "そうした話が本当かどうかを確かめます。有料記事の中で毎回使っている集計を、そのまま公開します。",
        "",
        "先にお伝えしておくと、この記事を読んでも当せん確率は上がりません。抽せんは毎回独立した無作為のものだからです。"
        "それでも「どんな形の数字が実際に出てきたのか」を知っておくと、自分で数字を選ぶときの納得感はずいぶん変わります。",
        "",
        _h("誤解1　よく出る数字・出にくい数字がある？"),
        f"ロト6の全{l6['total']:,}回で、1〜43の数字それぞれの出現回数に偏りがあるかをカイ二乗検定で調べると、"
        f"p値は{l6['chi_p']:.2f}でした。ロト7（全{l7['total']:,}回）は{l7['chi_p']:.2f}です。",
        "",
        "p値が0.05を下回ると「偶然では説明しにくい偏り」と判断されますが、どちらもそれよりはるかに大きい値です。"
        "つまり、長い目で見れば数字ごとの出やすさに差は見つかりません。",
        "",
        "ただし「直近20回」のような短い期間では、必ず偏りが出ます。これは偶然の揺れで、そこをどう扱うかが予想の分かれ目になります。",
        "",
        _h("誤解2　連番は出にくい？"),
        f"連続する数字（たとえば11と12）を含む回の割合は、ロト6で{l6['consec_all']:.0%}、ロト7では{l7['consec_all']:.0%}です。",
        "",
        "ロト6ではおよそ2回に1回、ロト7にいたっては4回に3回ほど連番が含まれています。"
        "「連番は避けたほうがいい」という話は、データの上では支持されません。",
        "",
        _h("誤解3　同じ数字が2つ入る形（ダブル）は珍しい？"),
        "ナンバーズ4の形の比率は次のとおりです。",
    ]
    for name, share in n4["pattern_all"]:
        P.append(f"・{name}：{share:.0%}")
    P += [
        "",
        f"4つとも違う数字（シングル）が{dict(n4['pattern_all']).get('シングル', 0):.0%}、"
        f"同じ数字を2つ含むダブルが{dict(n4['pattern_all']).get('ダブル', 0):.0%}。ダブルは2回に1回近く出ている、ごく普通の形です。",
        "",
        f"ナンバーズ3でも、ダブルは{dict(n3['pattern_all']).get('ダブル', 0):.0%}あります。",
        "",
        _h("誤解4　前回と同じ数字は出ない？"),
        f"ロト6で、前回と同じ数字が何個含まれるかを数えると、全回平均で{l6['carry_mean']:.2f}個でした。"
        f"0個だった回は{l6['carry_dist'][0]:.0%}、1個が{l6['carry_dist'][1]:.0%}、2個以上が{l6['carry_dist'][2]:.0%}です。",
        "",
        f"ナンバーズ4でも、前回と同じ桁に同じ数字が出た回は全体の{n4['repeat_rate']:.0%}あります。"
        "「前回出た数字は消す」という選び方は、実際にはよく起きている出来事を外していることになります。",
        "",
        _h("誤解5　合計値はバラバラ？"),
        f"ロト6の6つの数字の合計は、全体の8割が{l6['sum_lo']}〜{l6['sum_hi']}に収まっています（平均{l6['sum_mean']:.0f}）。"
        f"ロト7は{l7['sum_lo']}〜{l7['sum_hi']}（平均{l7['sum_mean']:.0f}）です。",
        "",
        "小さい数字ばかり、大きい数字ばかりを選ぶと、歴史的にほとんど出ていない形になります。",
        "",
        _h("データで言えること、言えないこと"),
        "ここまでの数字から言えるのは、「出目には形の傾向がある」ということだけです。"
        "どの数字が次に出るかは分かりませんし、分析によって当せん確率が上がることもありません。",
        "",
        "それでも、形の傾向を知っておけば、歴史的にまれな組み合わせを避けたり、逆に狙って選んだりといった判断が自分でできるようになります。",
    ]
    return title, "\n".join(_closing(P)), BASE_HASHTAGS + ["ロト6", "ロト7", "ナンバーズ", "統計"]


# ───────────────────────── 2. 直近1か月の出目レポート ─────────────────────────

def build_report(ctx: dict) -> tuple:
    loto, numbers, today = ctx["loto"], ctx["numbers"], ctx["today"]
    title = f"【{today.month}月の出目レポート】ロト・ナンバーズの直近の流れを数字で振り返る【無料・{MODEL_NAME}】"

    P = [
        f"{SEASON[today.month]}。直近の抽せん結果から、いまロトとナンバーズにどんな流れが来ているのかを整理しました。",
        "",
        "毎回の有料記事で使っている集計のうち、「直近の傾向」にあたる部分を無料で公開します。"
        "次に出る数字が分かるわけではありませんが、自分で数字を選ぶときの材料になります。",
        "",
    ]
    for key in ("loto6", "loto7"):
        a = loto[key]
        game = GAMES[key]
        hot = "　".join(f"{n:02d}（{a['f20'][n]}回）" for n in a["hot"][:5])
        cold = "　".join(f"{n:02d}（{a['interval'][n]}回未出現）" for n in a["cold"][:5])
        recent_avg = sum(a["recent_sums"]) / len(a["recent_sums"])
        P += [
            _h(f"{game.name}　直近の傾向"),
            f"・前回 第{a['last']['draw']}回の当せん番号：" + " ".join(f"{n:02d}" for n in a["last"]["main"]),
            f"・直近20回でよく出ている数字：{hot}",
            f"　（1つの数字あたりの期待値は{a['e20']:.1f}回です）",
            f"・長く出ていない数字：{cold}",
            f"・直近10回の合計値：{' → '.join(map(str, a['recent_sums']))}",
            f"　平均{recent_avg:.0f}。全回平均は{a['sum_mean']:.0f}なので、"
            + ("やや大きめの数字が選ばれている流れです。" if recent_avg > a["sum_mean"] else
               "やや小さめの数字が続いています。" if recent_avg < a["sum_mean"] else "ほぼ平均どおりです。"),
            f"・連番を含む回：直近20回で{a['consec_20']:.0%}（全回では{a['consec_all']:.0%}）",
            "",
        ]
    for key in ("numbers4", "numbers3"):
        a = numbers[key]
        game = GAMES[key]
        P += [_h(f"{game.name}　直近の傾向"),
              f"・前回 第{a['last']['draw']}回：{a['last']['number']}",
              "・直近10回：" + " → ".join(num for _, num in a["recent"]),
              "・直近30回で出現が多い数字（全桁合計）：" + "　".join(f"{g}（{c}回）" for g, c in a["digits_30"]),
              "・桁ごとの、いま出ている数字と沈黙している数字："]
        for pos in a["positions"]:
            P.append(f"　{pos['label']}　よく出る：{pos['hot'][0]}　／　出ていない：{pos['cold'][0]}（{pos['interval'][pos['cold'][0]]}回）")
        P.append("・パターン比率（直近30回）：" + "／".join(f"{k} {v:.0%}" for k, v in a["pattern_30"]))
        P.append("")

    P += [
        _h("この数字をどう使うか"),
        "直近の偏りは、長い目で見れば偶然の揺れです。ただ、その揺れをどう扱うかで数字の選び方は変わります。",
        "",
        "このノートの予想では、「よく出ている数字」「長く出ていない数字」「前回と同じ数字」「前回の隣の数字」「暦との重なり」などを"
        "それぞれ点数化し、毎週の検証結果に応じて重みを変えながら組み合わせています。",
    ]
    return title, "\n".join(_closing(P)), BASE_HASHTAGS + ["ロト6", "ロト7", "ナンバーズ予想", "出目"]


# ───────────────────────── 3. 暦カレンダー ─────────────────────────

def build_koyomi(ctx: dict) -> tuple:
    today = ctx["today"]
    end = today + timedelta(days=30)
    title = f"【{today.month}月〜{end.month}月】宝くじを買うならこの日｜天赦日・一粒万倍日・大安の暦カレンダー【無料・{MODEL_NAME}】"

    rows, lucky_days = [], []
    day = today
    while day <= end:
        ko = koyomi(day)
        draws = [GAMES[k].name for k in ("loto6", "loto7", "miniloto", "numbers4")
                 if is_draw_day(GAMES[k], day)]
        draw_text = "／".join("ナンバーズ" if n == "ナンバーズ4" else n for n in draws)
        rows.append((day, ko, draw_text))
        if ko["lucky_days"]:
            lucky_days.append((day, ko))
        day += timedelta(days=1)

    P = [
        f"{SEASON[today.month]}。宝くじを買う日を暦で選ぶ人は少なくありません。",
        "",
        f"この記事では、{ymd_ja(today)}から{ymd_ja(end)}までの暦を一覧にしました。"
        "天赦日や一粒万倍日といった吉日と、ロト・ナンバーズの抽せん日を並べています。",
        "",
        "暦で当せん確率が変わるわけではありません。それでも「この日に買う」と決めると、"
        "抽せんまでの時間が少し楽しみになります。そういう使い方のための一覧です。",
        "",
        _h("この期間の吉日"),
    ]
    if lucky_days:
        for day, ko in lucky_days:
            P.append(f"■ {ymd_ja(day)}　{'・'.join(ko['lucky_days'])}（六曜は{ko['rokuyo']}）")
    else:
        P.append("この期間に暦注の吉日はありません。")
    P += ["", _h("吉日の意味")]
    for name in ("天赦日", "一粒万倍日", "寅の日", "巳の日"):
        P.append(f"■ {name}")
        P.append(f"　{LUCKY_DETAIL[name]}")

    P += ["", _h("暦と抽せん日のカレンダー"), "日付／六曜／九星／吉日／抽せん"]
    for day, ko, draws in rows:
        lucky = "・".join(ko["lucky_days"])
        mark = "★" if lucky else ("○" if ko["rokuyo"] == "大安" else "　")
        line = f"{mark} {md_wd(day)}　{ko['rokuyo']}／{ko['kyusei_name']}"
        if lucky:
            line += f"／{lucky}"
        if draws:
            line += f"　【{draws}】"
        P.append(line)
    P += ["", "★＝暦注の吉日がある日、○＝大安の日です。"]
    return title, "\n".join(_closing(P)), BASE_HASHTAGS + ["開運", "一粒万倍日", "天赦日", "暦"]


BUILDERS = {"myths": build_myths, "report": build_report, "koyomi": build_koyomi}


def build(topic: str, ctx: dict) -> tuple:
    return BUILDERS[topic](ctx)
