#!/usr/bin/env python3
"""从零重建五大联赛(英超/西甲/意甲/德甲/法甲)——数据全部来自免费公开的
football-data.co.uk CSV(比分 + 半场 + 角球 + 赔率),无需任何 API key。
产出:games/<af>/data/{matches.json,corners.json} 与 games/<af>/{ratings.json,corners_ratings.json}。
用法:python3 build.py            # 默认近 14 个赛季 2012/13–2025/26
"""
import os, sys, csv, io, json, subprocess, datetime as dt

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from core.ratings import PoissonRatings

FDMAP = {39: "E0", 140: "SP1", 135: "I1", 78: "D1", 61: "F1"}
SEASONS = ["1213", "1314", "1415", "1516", "1617", "1718", "1819",
           "1920", "2021", "2122", "2223", "2324", "2425", "2526"]


def _csv(token, code):
    url = f"https://www.football-data.co.uk/mmz4281/{token}/{code}.csv"
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=25) as r:
            raw = r.read().decode("latin-1")
    except Exception:
        raw = subprocess.run(["curl", "-s", "--max-time", "25", url],
                             capture_output=True, text=True, timeout=30).stdout
    return list(csv.DictReader(io.StringIO(raw))) if raw.strip() else []


def _iso(d):
    for f in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return dt.datetime.strptime(d.strip(), f).date().isoformat()
        except Exception:
            pass
    return None


def build(af, code):
    cfg = json.load(open(os.path.join(ROOT, "games", str(af), "config.json"), encoding="utf-8"))
    matches, corners = [], []
    for tok in SEASONS:
        yr = 2000 + int(tok[:2])
        for r in _csv(tok, code):
            ht, at = r.get("HomeTeam"), r.get("AwayTeam")
            iso = _iso(r.get("Date", "")) if r.get("Date") else None
            if not ht or not at or not iso:
                continue
            try:
                matches.append({"date": iso, "season": yr, "home": ht, "away": at,
                                "hg": int(float(r["FTHG"])), "ag": int(float(r["FTAG"]))})
            except Exception:
                pass
            try:
                corners.append({"date": iso, "season": yr, "home": ht, "away": at,
                                "hc": int(float(r["HC"])), "ac": int(float(r["AC"]))})
            except Exception:
                pass
    matches.sort(key=lambda m: (m["date"], m["home"]))
    corners.sort(key=lambda m: (m["date"], m["home"]))
    dd = os.path.join(ROOT, "games", str(af), "data"); os.makedirs(dd, exist_ok=True)
    json.dump(matches, open(os.path.join(dd, "matches.json"), "w"), ensure_ascii=False)
    json.dump(corners, open(os.path.join(dd, "corners.json"), "w"), ensure_ascii=False)

    Rg = PoissonRatings(lg_goal=cfg.get("lg_goal", 1.35), lr=cfg.get("lr", 0.03),
                        season_reset=cfg.get("season_reset", 1.0)).fit(matches)
    g = Rg.snapshot(); g["updated_from"] = len(matches); g["last_date"] = max(m["date"] for m in matches)
    json.dump(g, open(os.path.join(ROOT, "games", str(af), "ratings.json"), "w"), ensure_ascii=False)

    cm = [{"home": c["home"], "away": c["away"], "hg": c["hc"], "ag": c["ac"], "season": c["season"]} for c in corners]
    mean_c = sum(c["hc"] + c["ac"] for c in corners) / (2 * len(corners)) if corners else 5.0
    Rc = PoissonRatings(lg_goal=mean_c, lr=cfg.get("lr", 0.03),
                        season_reset=cfg.get("season_reset", 1.0)).fit(cm)
    c = Rc.snapshot(); c["updated_from"] = len(cm); c["last_date"] = max(x["date"] for x in corners)
    json.dump(c, open(os.path.join(ROOT, "games", str(af), "corners_ratings.json"), "w"), ensure_ascii=False)
    print(f"[{af}] {cfg['name']}: 比分 {len(matches)} 场,角球 {len(corners)} 场,{len(g['teams'])} 队")


if __name__ == "__main__":
    for af, code in FDMAP.items():
        build(af, code)
