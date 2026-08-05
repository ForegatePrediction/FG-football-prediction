#!/usr/bin/env python3
"""每日刷新:增量续训各赛事评级快照。
- 载入现有 ratings.json -> 只拉当前赛季新赛果 -> 续训 -> 覆盖快照(仅提交 *.json 快照)。
- 池A 各联赛独立;跨联赛俱乐部池(_clubpool)/国家队池(_natpool)用相关赛事新赛果续训。
需环境变量 APIFOOTBALL_KEY。用法:python3 refresh.py
"""
import os, json, sys, datetime
try:
    import requests
except ImportError:
    requests = None
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.ratings import PoissonRatings

ROOT = os.path.dirname(os.path.abspath(__file__))
KEY = os.environ.get("APIFOOTBALL_KEY", "")
B = "https://v3.football.api-sports.io"
CUR = [datetime.date.today().year, datetime.date.today().year - 1]  # 当前+上一年,覆盖跨年赛季


def _get(path):
    r = requests.get(B + path, headers={"x-apisports-key": KEY}, timeout=30)
    return r.json()


def new_matches(af, after_date):
    out = []
    for s in CUR:
        try:
            resp = _get(f"/fixtures?league={af}&season={s}").get("response", [])
        except Exception:
            continue
        for m in resp:
            if m["fixture"]["status"]["short"] != "FT":
                continue
            g = m["goals"]
            if g["home"] is None or g["away"] is None:
                continue
            d = m["fixture"]["date"][:10]
            if after_date and d <= after_date:
                continue
            out.append({"date": d, "home": m["teams"]["home"]["name"],
                        "away": m["teams"]["away"]["name"], "hg": g["home"], "ag": g["away"]})
    return sorted(out, key=lambda m: (m["date"], m["home"]))


def refresh_league(af):
    p = os.path.join(ROOT, "games", str(af), "ratings.json")
    if not os.path.isfile(p):
        return
    snap = json.load(open(p, encoding="utf-8"))
    cfg = json.load(open(os.path.join(ROOT, "games", str(af), "config.json"), encoding="utf-8"))
    R = PoissonRatings.from_snapshot(snap, lg_goal=cfg.get("lg_goal", 1.35), lr=cfg.get("lr", 0.03))
    ms = new_matches(af, snap.get("last_date"))
    if not ms:
        return 0
    for m in ms:
        R.update(m["home"], m["away"], m["hg"], m["ag"])
    ns = R.snapshot()
    ns["last_date"] = max(m["date"] for m in ms)
    json.dump(ns, open(p, "w", encoding="utf-8"), ensure_ascii=False)
    return len(ms)


def main():
    if not KEY or requests is None:
        print("缺少 APIFOOTBALL_KEY 或 requests,退出"); sys.exit(1)
    rows = json.load(open(os.path.join(ROOT, "master_mapping.json"), encoding="utf-8"))
    afids = sorted({r["af_id"] for r in rows})
    total = 0
    for af in afids:
        try:
            n = refresh_league(af) or 0
            total += n
            if n:
                print(f"[{af}] +{n} 场")
        except Exception as e:
            print(f"[{af}] 失败 {str(e)[:60]}")
    print(f"刷新完成,新增合计 {total} 场")


if __name__ == "__main__":
    main()
