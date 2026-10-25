#!/usr/bin/env python3
"""每日刷新(按日期增量,极省 API 额度)。
思路:用 /fixtures?date=YYYY-MM-DD 一次拿当天全球所有已结束比赛,再筛出本项目的联赛,
增量续训对应评级快照。每天只拉"上次~今天"的几个日期 ≈ 1–7 次调用/天(免费档 100/天足够)。
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
MAX_LOOKBACK = 90  # 最多回看天数,避免长期未跑时范围过大


def _get(path):
    r = requests.get(B + path, headers={"x-apisports-key": KEY}, timeout=30)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, dict) or data.get("errors") or not isinstance(data.get("response"), list):
        raise RuntimeError("API-Sports 响应错误或订阅失效，拒绝将失败当成无比赛")
    return data


def pool_a_leagues():
    """本项目建了独立评级快照的联赛(池 A):league_id -> 快照路径。"""
    rows = json.load(open(os.path.join(ROOT, "master_mapping.json"), encoding="utf-8"))
    out = {}
    for r in rows:
        if r.get("pool") != "A":
            continue
        p = os.path.join(ROOT, "games", str(r["af_id"]), "ratings.json")
        if os.path.isfile(p):
            out[r["af_id"]] = p
    return out


def main():
    if "--enable-paid-api" not in sys.argv:
        sys.exit("付费 API 已暂停；续费后显式传入 --enable-paid-api")
    if not KEY or requests is None:
        print("缺少 APIFOOTBALL_KEY 或 requests,退出"); sys.exit(1)
    leagues = pool_a_leagues()
    snaps = {af: json.load(open(p, encoding="utf-8")) for af, p in leagues.items()}
    # 起始日期 = 各快照 last_date 的最小值(即最久没更新的那个),回看上限 MAX_LOOKBACK 天
    today = datetime.date.today()
    lds = [s.get("last_date") for s in snaps.values() if s.get("last_date")]
    start = (datetime.date.fromisoformat(min(lds)) + datetime.timedelta(days=1)) if lds else today - datetime.timedelta(days=1)
    # 按日期拉当天已结束比赛,归集到各联赛
    by_league = {af: [] for af in leagues}
    d = start; days = 0
    while d <= today:
        resp = _get(f"/fixtures?date={d.isoformat()}")["response"]
        for m in resp:
            lid = m["league"]["id"]
            if lid not in leagues or m["fixture"]["status"]["short"] != "FT":
                continue
            g = m["goals"]
            if g["home"] is None or g["away"] is None:
                continue
            by_league[lid].append({"date": m["fixture"]["date"][:10],
                                   "home": m["teams"]["home"]["name"], "away": m["teams"]["away"]["name"],
                                   "hg": g["home"], "ag": g["away"]})
        d += datetime.timedelta(days=1); days += 1
    # 增量续训
    total = 0
    for af, snap in snaps.items():
        ms = [x for x in by_league[af] if not snap.get("last_date") or x["date"] > snap["last_date"]]
        if not ms:
            continue
        ms.sort(key=lambda x: (x["date"], x["home"]))
        cfg = json.load(open(os.path.join(ROOT, "games", str(af), "config.json"), encoding="utf-8"))
        R = PoissonRatings.from_snapshot(snap, lg_goal=cfg.get("lg_goal", 1.35), lr=cfg.get("lr", 0.03))
        for m in ms:
            R.update(m["home"], m["away"], m["hg"], m["ag"])
        ns = R.snapshot(); ns["last_date"] = max(m["date"] for m in ms)
        json.dump(ns, open(leagues[af], "w", encoding="utf-8"), ensure_ascii=False)
        total += len(ms); print(f"[{af}] +{len(ms)} 场")
    print(f"刷新完成:拉取 {days} 个日期,新增合计 {total} 场,更新 {sum(1 for af in snaps if by_league[af])} 个联赛")


if __name__ == "__main__":
    main()
