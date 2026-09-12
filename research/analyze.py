import json, re, collections, statistics as st
from datetime import datetime, timezone, timedelta
N = json.load(open("notes.json", encoding="utf-8"))
print("total notes", len(N))
def typ(t):
    for k, p in [("ロト7", r"ロト\s?7|LOTO\s?7|ロトセブン"), ("ロト6", r"ロト\s?6|LOTO\s?6|ロトシックス"), ("ミニロト", r"ミニロト"),
                 ("ナンバーズ4", r"ナンバーズ\s?4|N4"), ("ナンバーズ3", r"ナンバーズ\s?3|N3"), ("ナンバーズ", r"ナンバーズ"),
                 ("ビンゴ5", r"ビンゴ\s?5|BINGO"), ("ジャンボ", r"ジャンボ"), ("toto/BIG", r"toto|BIG"), ("スクラッチ", r"スクラッチ")]:
        if re.search(p, t, re.I): return k
    return "宝くじ一般"
now = datetime(2026, 9, 13, tzinfo=timezone(timedelta(hours=9)))
for n in N:
    n["type"] = typ(n["title"]); n["paid"] = (n["price"] or 0) > 0 or n.get("is_free") is False
    try: n["dt"] = datetime.fromisoformat(n["date"])
    except: n["dt"] = None
paid = [n for n in N if n["paid"]]
print("paid", len(paid), f"{len(paid)/len(N):.0%}")
print("\n== by type: count / paid / paid% / median price / avg likes")
g = collections.defaultdict(list)
for n in N: g[n["type"]].append(n)
for k, v in sorted(g.items(), key=lambda x: -len(x[1])):
    p = [x for x in v if x["paid"]]; pr = [x["price"] for x in p if x["price"]]
    rec = [x for x in v if x["dt"] and (now - x["dt"]).days <= 30]
    print(f"{k:10} {len(v):5} paid {len(p):4} ({len(p)/len(v):.0%}) median¥{st.median(pr) if pr else '-'} likes{st.mean([x['likes'] for x in v]):.1f} last30d {len(rec)}")
print("\n== price distribution (paid)")
c = collections.Counter()
for n in paid:
    p = n["price"]; b = "0(sub/magazine)" if not p else ("100" if p <= 100 else "101-300" if p <= 300 else "301-500" if p <= 500 else "501-1000" if p <= 1000 else "1001-3000" if p <= 3000 else "3000+")
    c[b] += 1
print(c.most_common())
print("\n== last 30d posts by author (top 25)")
rec = [n for n in N if n["dt"] and (now - n["dt"]).days <= 30]
print("last30d total", len(rec), "paid", sum(n["paid"] for n in rec))
a = collections.defaultdict(list)
for n in rec: a[(n["user"], n["nickname"])].append(n)
for (u, nick), v in sorted(a.items(), key=lambda x: -len(x[1]))[:25]:
    pr = [x["price"] for x in v if x["paid"]]
    print(f"{u} {nick} posts{len(v)} paid{len(pr)} prices{sorted(set(pr))[:5]} likes{sum(x['likes'] for x in v)} types{collections.Counter(x['type'] for x in v).most_common(3)}")
print("\n== top liked paid notes")
for n in sorted(paid, key=lambda x: -x["likes"])[:30]:
    print(n["likes"], n["price"], n["type"], n["date"][:10] if n["date"] else "", n["user"], n["title"][:60])
print("\n== top liked free notes")
for n in sorted([n for n in N if not n["paid"]], key=lambda x: -x["likes"])[:20]:
    print(n["likes"], n["type"], n["date"][:10] if n["date"] else "", n["user"], n["title"][:60])
print("\n== title words")
w = collections.Counter()
for n in N:
    for k in ["予想","AI","統計","データ","分析","的中","当選","厳選","無料","有料","限定","買い目","キャリーオーバー","高額当選","占い","風水","開運","数秘","引き寄せ","スピリチュアル","攻略","確率","法則","出目","セット","ボックス","ストレート","ChatGPT","検証","結果","実績","億"]:
        if k in n["title"]: w[k] += 1
print(w.most_common())
print("\n== title words among paid")
w = collections.Counter()
for n in paid:
    for k in ["予想","AI","統計","データ","分析","的中","当選","厳選","限定","買い目","キャリーオーバー","占い","風水","開運","数秘","攻略","確率","法則","出目","ChatGPT","検証","実績","億","本命","激熱","必勝"]:
        if k in n["title"]: w[k] += 1
print(w.most_common())
print("\n== posts by weekday (last 90d)")
wd = collections.Counter(n["dt"].strftime("%a") for n in N if n["dt"] and (now - n["dt"]).days <= 90)
print(wd); hr = collections.Counter(n["dt"].hour for n in N if n["dt"] and (now - n["dt"]).days <= 90); print(sorted(hr.items()))
print("\n== year distribution"); print(sorted(collections.Counter(n["dt"].year for n in N if n["dt"]).items()))
