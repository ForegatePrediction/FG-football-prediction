#!/usr/bin/env python3
"""读取某赛事的 config + ratings 快照,零训练秒出全部玩法。
支持:模型概率 + (可选)盘口去水隐含概率 + 分歧 的混合口径;三语理由;队名模糊匹配。"""
import json, os
from .ratings import PoissonRatings
from .markets import markets, markets_ht, markets_corners
from .odds import devig_shin, divergence

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAMES = os.path.join(ROOT, "games")


def _load(code):
    d = os.path.join(GAMES, str(code))
    cfg = json.load(open(os.path.join(d, "config.json"), encoding="utf-8"))
    # 杯赛/洲际赛(池 B/C)不建自己的评级,而是引用统一俱乐部池
    ref = cfg.get("pool_ref")
    snap_dir = os.path.join(GAMES, str(ref)) if ref else d
    snap = json.load(open(os.path.join(snap_dir, "ratings.json"), encoding="utf-8"))
    return cfg, snap


import unicodedata as _ud, re as _re

_ABBR = {"man": "manchester", "utd": "united", "fc": "", "cf": "", "afc": "", "sc": "", "cd": "",
         "la": "losangeles", "ny": "newyork", "nyc": "newyork", "psg": "parissaintgermain",
         "spurs": "tottenham", "wolves": "wolverhampton", "inter": "internazionale", "atleti": "atletico",
         "st": "saint", "utd.": "united", "w": ""}


def _toks(s):
    s = _ud.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    s = _re.sub(r"[^a-z0-9 ]", " ", s)
    out = []
    for t in s.split():
        t = _ABBR.get(t, t)
        if t:
            out.append(t)
    return out


def _find(teams, name):
    if name in teams:
        return name
    nl = name.lower().strip()
    # 1) 子串包含(双向),选出场最多
    c = [t for t in teams if nl in t.lower() or t.lower() in nl]
    if c:
        return max(c, key=lambda t: teams[t].get("gp", 0))
    # 2) 词级模糊:token 重叠 + 缩写扩展,阈值命中
    q = set(_toks(name))
    if not q:
        return None
    best, bs = None, 0.0
    for t in teams:
        tt = set(_toks(t))
        if not tt:
            continue
        inter = len(q & tt)
        # 子串型 token 补偿(manchester 含 man)
        sub = sum(1 for a in q for b in tt if len(a) > 3 and (a in b or b in a))
        score = (inter + 0.5 * sub) / max(len(q), len(tt))
        if score > bs:
            best, bs = t, score
    return best if bs >= 0.5 else None


def _reasons(A, B, mk, lang):
    o = mk["one_x_two"]; eg = mk["expected_goals"]; ou = mk["over_under"]["2.5"]
    pc = lambda x: f"{round(x*100)}%"
    picks = [("home", A, o["home"]), ("draw", None, o["draw"]), ("away", B, o["away"])]
    top = max(picks, key=lambda x: x[2])
    if lang == "en":
        pk = "Draw" if top[0] == "draw" else top[1]
        return {
            "one_x_two": [f"Expected goals {A} {eg['home']} : {eg['away']} {B}",
                          f"Model lean: {pk} {pc(top[2])} (H {pc(o['home'])}/D {pc(o['draw'])}/A {pc(o['away'])})"],
            "over_under": [f"Total goals over {ou['line']}: {pc(ou['over'])}"],
            "btts": [f"Both teams to score: {pc(mk['btts']['yes'])}"],
        }
    if lang == "vi":
        pk = "Hòa" if top[0] == "draw" else top[1]
        return {
            "one_x_two": [f"Bàn thắng kỳ vọng {A} {eg['home']} : {eg['away']} {B}",
                          f"Mô hình nghiêng: {pk} {pc(top[2])} (Thắng {pc(o['home'])}/Hòa {pc(o['draw'])}/Thua {pc(o['away'])})"],
            "over_under": [f"Tài {ou['line']} bàn: {pc(ou['over'])}"],
            "btts": [f"Cả hai đội ghi bàn: {pc(mk['btts']['yes'])}"],
        }
    pk = "平局" if top[0] == "draw" else top[1]
    return {
        "one_x_two": [f"预期进球 {A} {eg['home']} : {eg['away']} {B}",
                      f"模型倾向:{pk} {pc(top[2])}(主 {pc(o['home'])}/平 {pc(o['draw'])}/客 {pc(o['away'])})"],
        "over_under": [f"大于 {ou['line']} 球概率:{pc(ou['over'])}"],
        "btts": [f"双方进球概率:{pc(mk['btts']['yes'])}"],
    }


def predict(code, A, B, hcap=0.0, total=2.5, lang="zh", odds_1x2=None):
    cfg, snap = _load(code)
    teams = snap["teams"]
    a, b = _find(teams, A), _find(teams, B)
    if not a or not b:
        return {"error": f"未找到:{A if not a else B}", "missing": A if not a else B}
    rho = cfg.get("rho", -0.06)
    lh, la = PoissonRatings.rates_from_snapshot(snap, a, b)
    mk = markets(lh, la, rho)
    mk.update(markets_ht(lh, la, rho, fh_share=cfg.get("fh_share", 0.458)))  # 半场类玩法
    # 角球玩法(仅有角球快照的联赛;football-data 覆盖的主流联赛)
    cpath = os.path.join(GAMES, str(code), "corners_ratings.json")
    if os.path.isfile(cpath):
        csnap = json.load(open(cpath, encoding="utf-8"))
        ca, cb = _find(csnap["teams"], a), _find(csnap["teams"], b)
        if ca and cb:
            lch, lca = PoissonRatings.rates_from_snapshot(csnap, ca, cb)
            mk.update(markets_corners(lch, lca))
    out = {"code": str(code), "competition": cfg.get("name"), "category_id": cfg.get("category_id"),
           "pool": cfg.get("pool"), "A": a, "B": b, "lang": lang,
           "matched_exact": (A == a and B == b), "markets": mk,
           "reasons": _reasons(a, b, mk, lang)}
    # 混合口径:若给了盘口 1X2 赔率,附市场隐含概率 + 分歧(不融合成单值)
    if odds_1x2:
        m = mk["one_x_two"]; model = [m["home"], m["draw"], m["away"]]
        market = devig_shin(odds_1x2)
        out["market"] = {"one_x_two": {"home": market[0], "draw": market[1], "away": market[2]}} if market else None
        out["divergence"] = divergence(model, market, ["home", "draw", "away"]) if market else None
    return out


def list_teams(code, kw):
    _, snap = _load(code)
    kw = kw.lower()
    hits = [(t, v) for t, v in snap["teams"].items() if kw in t.lower()]
    return sorted(hits, key=lambda x: -x[1]["gp"])
