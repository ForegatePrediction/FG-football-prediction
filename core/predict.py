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


def _pc(x):
    return f"{round((x or 0) * 100)}%"


def _pick_line(d, key, target=0.5):
    """从多条盘口线里挑最接近 target(默认 0.5,最主流/最有信息量)的一条。"""
    best, bd = None, 9.0
    if not d:
        return None
    for k in d:
        e = d[k]
        v = e.get(key)
        if v is None:
            continue
        if abs(v - target) < bd:
            bd, best = abs(v - target), e
    return best


def _reasons(A, B, mk, p, lang, is_cup):
    """逐玩法量化依据,key 与 platform_markets 对齐(前端可 reasons[平台key] 直取)。
    覆盖:moneyline/spreads/totals/both_teams_to_score/soccer_exact_score/
         soccer_team_totals/soccer_first_to_score/total_corners(有角球快照时)/
         杯赛专属 soccer_team_to_advance + soccer_penalty_shootout。三语:zh(繁體)/en/vi。"""
    pc = _pc
    eg = mk["expected_goals"]; o = mk["one_x_two"]
    picks = [("home", A, o["home"]), ("draw", None, o["draw"]), ("away", B, o["away"])]
    top = max(picks, key=lambda x: x[2])
    sp = _pick_line(p.get("spreads"), "home") or {}
    tot = (p.get("totals") or {}).get("2.5") or _pick_line(p.get("totals"), "over") or {}
    bt = p.get("both_teams_to_score") or {}
    cs = (p.get("soccer_exact_score") or [])[:3]
    tt = p.get("soccer_team_totals") or {}
    tth = ((tt.get("home") or {}).get("1.5")) or {}
    tta = ((tt.get("away") or {}).get("0.5")) or {}
    fs = p.get("soccer_first_to_score") or {}
    corn = p.get("total_corners"); ec = mk.get("expected_corners")
    cl = _pick_line(corn, "over") if corn else None
    ect = (ec or {}).get("total", "—")
    cs_str = " · ".join(f"{s} {pc(pr)}" for s, pr in cs)

    if lang == "en":
        pk = "Draw" if top[0] == "draw" else top[1]
        r = {
            "moneyline": [f"Expected goals {A} {eg['home']} : {eg['away']} {B}",
                          f"Model lean: {pk} {pc(top[2])} (H {pc(o['home'])}/D {pc(o['draw'])}/A {pc(o['away'])})"],
            "totals": [f"Over {tot.get('line')} goals {pc(tot.get('over'))}; under {pc(tot.get('under'))}"],
            "both_teams_to_score": [f"Both teams to score: yes {pc(bt.get('yes'))} · no {pc(bt.get('no'))}"],
            "soccer_team_totals": [f"{A} exp {eg['home']} (over 1.5 {pc(tth.get('over'))}); {B} exp {eg['away']} (over 0.5 {pc(tta.get('over'))})"],
            "soccer_first_to_score": [f"First to score: {A} {pc(fs.get('home'))} · {B} {pc(fs.get('away'))} · none {pc(fs.get('none'))}"],
        }
        if cs: r["soccer_exact_score"] = [f"Most likely scores: {cs_str}"]
        if sp: r["spreads"] = [f"Handicap {sp.get('line')} (for {A}): cover {pc(sp.get('home'))} · push {pc(sp.get('push'))} · lose {pc(sp.get('away'))}"]
        if cl: r["total_corners"] = [f"Expected corners {ect}; over {cl.get('line')} {pc(cl.get('over'))}"]
    elif lang == "vi":
        pk = "Hòa" if top[0] == "draw" else top[1]
        r = {
            "moneyline": [f"Bàn kỳ vọng {A} {eg['home']} : {eg['away']} {B}",
                          f"Mô hình nghiêng: {pk} {pc(top[2])} (Thắng {pc(o['home'])}/Hòa {pc(o['draw'])}/Thua {pc(o['away'])})"],
            "totals": [f"Tài {tot.get('line')} bàn {pc(tot.get('over'))}; Xỉu {pc(tot.get('under'))}"],
            "both_teams_to_score": [f"Cả hai ghi bàn: Có {pc(bt.get('yes'))} · Không {pc(bt.get('no'))}"],
            "soccer_team_totals": [f"{A} kỳ vọng {eg['home']} (Tài 1.5 {pc(tth.get('over'))}); {B} kỳ vọng {eg['away']} (Tài 0.5 {pc(tta.get('over'))})"],
            "soccer_first_to_score": [f"Ghi bàn trước: {A} {pc(fs.get('home'))} · {B} {pc(fs.get('away'))} · không {pc(fs.get('none'))}"],
        }
        if cs: r["soccer_exact_score"] = [f"Tỉ số khả dĩ nhất: {cs_str}"]
        if sp: r["spreads"] = [f"Chấp {sp.get('line')} (cho {A}): thắng kèo {pc(sp.get('home'))} · hòa vốn {pc(sp.get('push'))} · thua {pc(sp.get('away'))}"]
        if cl: r["total_corners"] = [f"Phạt góc kỳ vọng {ect}; Tài {cl.get('line')} {pc(cl.get('over'))}"]
    else:  # zh — 繁體中文
        pk = "和局" if top[0] == "draw" else top[1]
        r = {
            "moneyline": [f"預期進球 {A} {eg['home']} : {eg['away']} {B}",
                          f"模型傾向:{pk} {pc(top[2])}(主 {pc(o['home'])}/和 {pc(o['draw'])}/客 {pc(o['away'])})"],
            "totals": [f"大 {tot.get('line')} 球機率 {pc(tot.get('over'))};小 {pc(tot.get('under'))}"],
            "both_teams_to_score": [f"雙方進球:是 {pc(bt.get('yes'))} · 否 {pc(bt.get('no'))}"],
            "soccer_team_totals": [f"{A} 期望 {eg['home']} 球(大 1.5 {pc(tth.get('over'))});{B} 期望 {eg['away']} 球(大 0.5 {pc(tta.get('over'))})"],
            "soccer_first_to_score": [f"先進球:{A} {pc(fs.get('home'))} · {B} {pc(fs.get('away'))} · 無進球 {pc(fs.get('none'))}"],
        }
        if cs: r["soccer_exact_score"] = [f"最可能比分:{cs_str}"]
        if sp: r["spreads"] = [f"讓球 {sp.get('line')}(以 {A} 計):贏盤 {pc(sp.get('home'))} · 走盤 {pc(sp.get('push'))} · 輸盤 {pc(sp.get('away'))}"]
        if cl: r["total_corners"] = [f"期望角球 {ect};大 {cl.get('line')} 機率 {pc(cl.get('over'))}"]

    if is_cup:
        adv = p.get("soccer_team_to_advance") or {}; pen = p.get("soccer_penalty_shootout") or {}
        if lang == "en":
            r["soccer_team_to_advance"] = [f"To advance: {A} {pc(adv.get('home'))} · {B} {pc(adv.get('away'))}"]
            r["soccer_penalty_shootout"] = [f"Penalty shootout likelihood: {pc(pen.get('yes'))}"]
        elif lang == "vi":
            r["soccer_team_to_advance"] = [f"Đi tiếp: {A} {pc(adv.get('home'))} · {B} {pc(adv.get('away'))}"]
            r["soccer_penalty_shootout"] = [f"Khả năng đá luân lưu: {pc(pen.get('yes'))}"]
        else:
            r["soccer_team_to_advance"] = [f"晉級機率:{A} {pc(adv.get('home'))} · {B} {pc(adv.get('away'))}"]
            r["soccer_penalty_shootout"] = [f"進入十二碼大戰機率:{pc(pen.get('yes'))}"]
    return r


def _platform_markets(mk, lh, la, is_cup):
    """把内部字段映射成平台玩法 key,供前端直接按平台 key 取用。
    平台足球玩法:moneyline / spreads / totals / both_teams_to_score / soccer_exact_score /
                 soccer_team_totals / total_corners / soccer_first_to_score /
                 soccer_team_to_advance / soccer_penalty_shootout。"""
    o = mk["one_x_two"]
    p = {
        "moneyline": {"home": o["home"], "draw": o["draw"], "away": o["away"]},
        "spreads": mk["handicap"],                       # 多条让分线 {line,home,away,push}
        "totals": mk["over_under"],                      # 多条大小线 {line,over,under}
        "both_teams_to_score": mk["btts"],               # {yes,no}
        "soccer_exact_score": mk["correct_score"],       # [[比分,概率],...]
        "soccer_team_totals": {"home": mk["team_total_home"], "away": mk["team_total_away"]},
    }
    # 角球(仅角球快照覆盖的联赛有)
    if "corners_total" in mk:
        p["total_corners"] = mk["corners_total"]
    # 首先进球:home 先 / away 先 / 无进球(全场0-0)
    none = mk.get("neither_score_first", {}).get("yes")
    if none is None:
        import math
        none = math.exp(-(lh + la))
    s = lh + la
    p["soccer_first_to_score"] = {
        "home": (lh / s) * (1 - none) if s > 0 else 0.0,
        "away": (la / s) * (1 - none) if s > 0 else 0.0,
        "none": none,
    }
    # 淘汰赛专属:晋级 / 点球大战(联赛不适用,置 null)
    if is_cup:
        adv_h = o["home"] + 0.5 * o["draw"]
        p["soccer_team_to_advance"] = {"home": adv_h, "away": 1 - adv_h}
        # 单场平局约一半在加时分出、一半进点球
        pen = o["draw"] * 0.5
        p["soccer_penalty_shootout"] = {"yes": pen, "no": 1 - pen}
    else:
        p["soccer_team_to_advance"] = None
        p["soccer_penalty_shootout"] = None
    return p


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
    is_cup = (cfg.get("type") == "Cup") or (cfg.get("pool") in ("B", "C", "D"))
    pm = _platform_markets(mk, lh, la, is_cup)
    out = {"code": str(code), "competition": cfg.get("name"), "category_id": cfg.get("category_id"),
           "platform_id": cfg.get("platform_id"), "pool": cfg.get("pool"), "A": a, "B": b, "lang": lang,
           "matched_exact": (A == a and B == b), "markets": mk,
           "platform_markets": pm,
           "reasons": _reasons(a, b, mk, pm, lang, is_cup)}
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
