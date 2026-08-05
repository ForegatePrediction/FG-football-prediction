#!/usr/bin/env python3
"""每日增量刷新(免费数据源 football-data.co.uk,无需任何 API key)。
五大联赛(英超/西甲/意甲/德甲/法甲)每场的比分 + 半场 + 角球 + 赔率均由公开 CSV 提供。
只取「上次快照日期之后」的已结束比赛,增量续训进球评级与角球评级,写回快照。
每天仅下载当前赛季(必要时含上一赛季)各联赛一个 CSV —— 零成本、零密钥。
用法:python3 refresh.py
"""
import os, sys, json, csv, io, subprocess, datetime as dt

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from core.ratings import PoissonRatings

# af_id -> football-data.co.uk 联赛代码
FDMAP = {39: "E0", 140: "SP1", 135: "I1", 78: "D1", 61: "F1"}


def _season_tokens():
    """返回需要检查的赛季 token(当前赛季 + 上一赛季,覆盖赛季切换与收官)。"""
    t = dt.date.today()
    start = t.year if t.month >= 8 else t.year - 1   # 足球赛季约 8 月开踢
    toks = [f"{s % 100:02d}{(s + 1) % 100:02d}" for s in (start, start - 1)]
    return toks, start


def _csv_rows(token, code):
    url = f"https://www.football-data.co.uk/mmz4281/{token}/{code}.csv"
    raw = ""
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=25) as r:
            raw = r.read().decode("latin-1")
    except Exception:
        try:
            raw = subprocess.run(["curl", "-s", "--max-time", "25", url],
                                 capture_output=True, text=True, timeout=30).stdout
        except Exception:
            raw = ""
    if not raw.strip():
        return []
    return list(csv.DictReader(io.StringIO(raw)))


def _iso(d):
    for f in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return dt.datetime.strptime(d.strip(), f).date().isoformat()
        except Exception:
            pass
    return None


def _config(af):
    return json.load(open(os.path.join(ROOT, "games", str(af), "config.json"), encoding="utf-8"))


def _load(af, fname):
    p = os.path.join(ROOT, "games", str(af), fname)
    return json.load(open(p, encoding="utf-8")) if os.path.isfile(p) else None


def _append(af, rel, rows):
    p = os.path.join(ROOT, "games", str(af), rel)
    allr = json.load(open(p, encoding="utf-8")) if os.path.isfile(p) else []
    allr += rows
    json.dump(allr, open(p, "w", encoding="utf-8"), ensure_ascii=False)


def refresh_league(af, code, tokens, start_year):
    cfg = _config(af)
    gsnap = _load(af, "ratings.json")
    csnap = _load(af, "corners_ratings.json")
    if not gsnap:
        print(f"[{af}] 无进球快照,跳过"); return
    last = gsnap.get("last_date")
    rows = []
    for tok in tokens:
        for r in _csv_rows(tok, code):
            iso = _iso(r.get("Date", "")) if r.get("Date") else None
            if not iso or (last and iso <= last):
                continue
            season = start_year if tok == tokens[0] else start_year - 1
            try:
                hg = int(float(r["FTHG"])); ag = int(float(r["FTAG"]))
            except Exception:
                hg = ag = None
            try:
                hc = int(float(r["HC"])); ac = int(float(r["AC"]))
            except Exception:
                hc = ac = None
            rows.append({"date": iso, "season": season, "home": r.get("HomeTeam"),
                         "away": r.get("AwayTeam"), "hg": hg, "ag": ag, "hc": hc, "ac": ac})
    rows = [x for x in rows if x["home"] and x["away"]]
    rows.sort(key=lambda x: (x["date"], x["home"]))
    goals = [x for x in rows if x["hg"] is not None]
    corners = [x for x in rows if x["hc"] is not None]
    if not goals:
        print(f"[{af}] {cfg['name']}: 无新增"); return

    # 进球评级增量
    Rg = PoissonRatings.from_snapshot(gsnap, lg_goal=cfg.get("lg_goal", 1.35), lr=cfg.get("lr", 0.03))
    for m in goals:
        Rg.update(m["home"], m["away"], m["hg"], m["ag"], m["season"])
    g2 = Rg.snapshot(); g2["updated_from"] = gsnap.get("updated_from", 0) + len(goals)
    g2["last_date"] = max(m["date"] for m in goals)
    json.dump(g2, open(os.path.join(ROOT, "games", str(af), "ratings.json"), "w", encoding="utf-8"), ensure_ascii=False)
    _append(af, "data/matches.json",
            [{"date": m["date"], "season": m["season"], "home": m["home"], "away": m["away"],
              "hg": m["hg"], "ag": m["ag"]} for m in goals])

    # 角球评级增量
    if csnap and corners:
        Rc = PoissonRatings.from_snapshot(csnap, lr=cfg.get("lr", 0.03))
        for m in corners:
            Rc.update(m["home"], m["away"], m["hc"], m["ac"], m["season"])
        c2 = Rc.snapshot(); c2["updated_from"] = csnap.get("updated_from", 0) + len(corners)
        c2["last_date"] = max(m["date"] for m in corners)
        json.dump(c2, open(os.path.join(ROOT, "games", str(af), "corners_ratings.json"), "w", encoding="utf-8"), ensure_ascii=False)
        _append(af, "data/corners.json",
                [{"date": m["date"], "season": m["season"], "home": m["home"], "away": m["away"],
                  "hc": m["hc"], "ac": m["ac"]} for m in corners])

    print(f"[{af}] {cfg['name']}: +{len(goals)} 场(角球 +{len(corners)}) -> last_date {g2['last_date']}")


def main():
    tokens, start_year = _season_tokens()
    print(f"检查赛季 token: {tokens}")
    for af, code in FDMAP.items():
        refresh_league(af, code, tokens, start_year)


if __name__ == "__main__":
    main()
