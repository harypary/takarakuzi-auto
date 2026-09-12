import json, time, urllib.parse, urllib.request, re, sys
KW = ["ロト6","ロト7","ミニロト","ナンバーズ3","ナンバーズ4","ビンゴ5","ジャンボ宝くじ","宝くじ予想","宝くじ","着せかえクジ","toto","BIG","ロト 予想","ナンバーズ 予想","年末ジャンボ","サマージャンボ","宝くじ 高額当選","数字選択式"]
LOT = re.compile(r"ロト|ﾛﾄ|LOTO|loto|ナンバーズ|ミニロト|ビンゴ5|ジャンボ|宝くじ|たからくじ|toto|BIG|クジ|数字選択", re.I)
seen = {}
def get(url):
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
    for _ in range(3):
        try:
            return json.load(urllib.request.urlopen(req, timeout=20))
        except Exception as e:
            time.sleep(2)
    return None
for kw in KW:
    for sort in ["new","popular","like"]:
        for start in range(0, 400, 20):
            d = get(f"https://note.com/api/v3/searches?context=note&q={urllib.parse.quote(kw)}&size=20&start={start}&sort={sort}")
            if not d: break
            n = d["data"]["notes"]; cs = n.get("contents", [])
            for c in cs:
                if not LOT.search(c.get("name") or ""): continue
                u = c.get("user") or {}
                pi = c.get("price_info") or {}
                seen[c["key"]] = dict(key=c["key"], title=c["name"], price=c.get("price") or 0,
                    is_free=pi.get("is_free", True), sub=pi.get("has_subscription"), multiple=pi.get("has_multiple"),
                    lowest=pi.get("oneshot_lowest_price"), likes=c.get("like_count",0), comments=c.get("comment_count",0),
                    date=c.get("publish_at"), user=u.get("urlname"), nickname=u.get("nickname"),
                    member=c.get("is_membership_connected"), kw=kw)
            if n.get("is_last_page") or not cs: break
            time.sleep(0.4)
        print(kw, sort, len(seen), flush=True)
json.dump(list(seen.values()), open("notes.json","w",encoding="utf-8"), ensure_ascii=False)
