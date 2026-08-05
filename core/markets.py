#!/usr/bin/env python3
"""由期望进球 (λ_home, λ_away) 生成比分矩阵,再推出**全部进球类玩法**。
含 Dixon-Coles 低比分修正 rho。覆盖所有"全场进球可推导"的玩法(约 30+ 种)。
半场类玩法见 markets_ht(需半场进球模型);角球/牌数等需独立统计模型。"""
import math

_FACT = [math.factorial(i) for i in range(13)]


def _pois(k, lam):
    return math.exp(-lam) * lam ** k / _FACT[k]


def score_matrix(lh, la, rho=-0.06, N=11):
    ph = [_pois(i, lh) for i in range(N)]
    pa = [_pois(j, la) for j in range(N)]
    ph[-1] += max(0.0, 1 - sum(ph))
    pa[-1] += max(0.0, 1 - sum(pa))
    P = [[ph[i] * pa[j] for j in range(N)] for i in range(N)]
    if rho:
        tau = {(0, 0): 1 - lh * la * rho, (0, 1): 1 + lh * rho,
               (1, 0): 1 + la * rho, (1, 1): 1 - rho}
        for (i, j), f in tau.items():
            P[i][j] = max(P[i][j] * f, 0.0)
        s = sum(sum(r) for r in P)
        P = [[x / s for x in r] for r in P]
    return P


def _ou(P, line):
    over = sum(P[i][j] for i in range(len(P)) for j in range(len(P)) if i + j > line)
    return {"line": line, "over": over, "under": 1 - over}


def _team_ou(P, line, home=True):
    N = len(P)
    over = 0.0
    for i in range(N):
        for j in range(N):
            g = i if home else j
            if g > line:
                over += P[i][j]
    return {"line": line, "over": over, "under": 1 - over}


def _handicap(P, line, asian=True):
    """让球:line 为主队盘口(负=主队让).asian 时走盘平局按比例(此处整/半线通用给 home/away/push)。"""
    N = len(P)
    home = away = push = 0.0
    for i in range(N):
        for j in range(N):
            m = (i - j) + line
            if m > 1e-9: home += P[i][j]
            elif m < -1e-9: away += P[i][j]
            else: push += P[i][j]
    return {"line": line, "home": home, "away": away, "push": push}


def markets(lh, la, rho=-0.06, ou_lines=(0.5, 1.5, 2.5, 3.5, 4.5),
            hcap_lines=(-2, -1, 0, 1, 2), team_ou_lines=(0.5, 1.5, 2.5)):
    P = score_matrix(lh, la, rho)
    N = len(P)
    home = draw = away = btts = 0.0
    odd = even = h_odd = a_odd = 0.0
    cs_home = cs_away = wtn_home = wtn_away = 0.0
    hs = a_s = 0.0  # 主/客 至少进 1 球
    h2 = a2 = 0.0   # 主/客 两球+
    margin = {}     # 净胜球分布(home 视角:+2,+1,0,-1,...)
    exact_total = {}  # 总进球数分布
    scores = []
    for i in range(N):
        for j in range(N):
            p = P[i][j]
            if i > j: home += p
            elif i == j: draw += p
            else: away += p
            if i > 0 and j > 0: btts += p
            t = i + j
            if t % 2: odd += p
            else: even += p
            if i % 2: h_odd += p
            if j % 2: a_odd += p
            if j == 0: cs_home += p
            if i == 0: cs_away += p
            if i > j and j == 0: wtn_home += p
            if j > i and i == 0: wtn_away += p
            if i >= 1: hs += p
            if j >= 1: a_s += p
            if i >= 2: h2 += p
            if j >= 2: a2 += p
            margin[i - j] = margin.get(i - j, 0.0) + p
            exact_total[t] = exact_total.get(t, 0.0) + p
            scores.append((i, j, p))
    scores.sort(key=lambda x: -x[2])
    denom = home + away or 1e-9

    # 净胜球(winning margin)归并
    def mg(cond):
        return sum(v for k, v in margin.items() if cond(k))
    winning_margin = {
        "home_by_1": margin.get(1, 0.0), "home_by_2": margin.get(2, 0.0),
        "home_by_3+": mg(lambda k: k >= 3), "draw": margin.get(0, 0.0),
        "away_by_1": margin.get(-1, 0.0), "away_by_2": margin.get(-2, 0.0),
        "away_by_3+": mg(lambda k: k <= -3),
    }
    exact_goals = {str(g): exact_total.get(g, 0.0) for g in range(0, 6)}
    exact_goals["6+"] = sum(v for k, v in exact_total.items() if k >= 6)
    multigoals = {"0-1": mg2(exact_total, 0, 1), "2-3": mg2(exact_total, 2, 3),
                  "4-6": mg2(exact_total, 4, 6), "7+": sum(v for k, v in exact_total.items() if k >= 7)}

    return {
        "expected_goals": {"home": round(lh, 3), "away": round(la, 3)},
        # —— 主流胜负/让分/大小 ——
        "one_x_two": {"home": home, "draw": draw, "away": away},
        "double_chance": {"1X": home + draw, "12": home + away, "X2": draw + away},
        "dnb": {"home": home / denom, "away": away / denom},
        "over_under": {str(l): _ou(P, l) for l in ou_lines},
        "handicap": {str(l): _handicap(P, l) for l in hcap_lines},
        "btts": {"yes": btts, "no": 1 - btts},
        # —— 比分/进球数 ——
        "correct_score": [(f"{i}-{j}", round(p, 4)) for i, j, p in scores[:8]],
        "exact_goals": exact_goals,
        "multigoals": multigoals,
        "winning_margin": winning_margin,
        "odd_even": {"odd": odd, "even": even},
        "home_odd_even": {"odd": h_odd, "even": 1 - h_odd},
        "away_odd_even": {"odd": a_odd, "even": 1 - a_odd},
        # —— 球队维度 ——
        "team_total_home": {str(l): _team_ou(P, l, True) for l in team_ou_lines},
        "team_total_away": {str(l): _team_ou(P, l, False) for l in team_ou_lines},
        "team_score_home": {"yes": hs, "no": 1 - hs},
        "team_score_away": {"yes": a_s, "no": 1 - a_s},
        "team_2plus_home": {"yes": h2, "no": 1 - h2},
        "team_2plus_away": {"yes": a2, "no": 1 - a2},
        "clean_sheet_home": {"yes": cs_home, "no": 1 - cs_home},
        "clean_sheet_away": {"yes": cs_away, "no": 1 - cs_away},
        "win_to_nil_home": {"yes": wtn_home, "no": 1 - wtn_home},
        "win_to_nil_away": {"yes": wtn_away, "no": 1 - wtn_away},
        # —— 组合盘 ——
        "result_btts": {
            "home_yes": _combo(P, "home", True), "home_no": _combo(P, "home", False),
            "draw_yes": _combo(P, "draw", True), "draw_no": _combo(P, "draw", False),
            "away_yes": _combo(P, "away", True), "away_no": _combo(P, "away", False)},
        "result_ou25": {
            "home_over": _combo_ou(P, "home", 2.5, True), "home_under": _combo_ou(P, "home", 2.5, False),
            "draw_over": _combo_ou(P, "draw", 2.5, True), "draw_under": _combo_ou(P, "draw", 2.5, False),
            "away_over": _combo_ou(P, "away", 2.5, True), "away_under": _combo_ou(P, "away", 2.5, False)},
    }


def _half_block(lh, la, rho, ou_lines):
    """给定该半场的期望进球,产出该半场的 胜平负 / 大小球 / BTTS。"""
    P = score_matrix(lh, la, rho, N=8)
    N = len(P); home = draw = away = btts = 0.0
    for i in range(N):
        for j in range(N):
            p = P[i][j]
            if i > j: home += p
            elif i == j: draw += p
            else: away += p
            if i > 0 and j > 0: btts += p
    return {"result": {"home": home, "draw": draw, "away": away},
            "over_under": {str(l): _ou(P, l) for l in ou_lines},
            "btts": {"yes": btts, "no": 1 - btts}}, P


def markets_ht(lh, la, rho=-0.06, fh_share=0.458, ou_lines=(0.5, 1.5, 2.5)):
    """半场类玩法:上/下半场 胜平负、大小球、BTTS;半场平;最高进球半场;谁都不先进球。
    近似:每半场为独立泊松,球队期望进球按 fh_share 拆分(上半场占比,联赛实测 ~0.458)。"""
    lh1, la1 = lh * fh_share, la * fh_share
    lh2, la2 = lh * (1 - fh_share), la * (1 - fh_share)
    fh, P1 = _half_block(lh1, la1, rho, ou_lines)
    sh, P2 = _half_block(lh2, la2, rho, ou_lines)
    # 最高进球半场(两半场独立近似)
    import math as _m
    def tot_dist(l1, l2):
        d = {}
        for k in range(9):
            d[k] = _m.exp(-(l1 + l2)) * (l1 + l2) ** k / _FACT[k]
        return d
    d1, d2 = tot_dist(lh1, la1), tot_dist(lh2, la2)
    first = equal = second = 0.0
    for a in range(9):
        for b in range(9):
            p = d1[a] * d2[b]
            if a > b: first += p
            elif a == b: equal += p
            else: second += p
    # 谁都不先进球 = 全场 0-0
    p00 = _pois(0, lh) * _pois(0, la)
    return {
        "first_half": fh,
        "second_half": sh,
        "ht_result": fh["result"],
        "highest_scoring_half": {"first": first, "equal": equal, "second": second},
        "neither_score_first": {"yes": p00, "no": 1 - p00},
    }


def _pois_big(k, lam):
    return math.exp(-lam + k * math.log(lam) - math.lgamma(k + 1)) if lam > 0 else (1.0 if k == 0 else 0.0)


def markets_corners(lc_home, lc_away, total_lines=(8.5, 9.5, 10.5, 11.5, 12.5),
                    team_lines=(3.5, 4.5, 5.5), N=30):
    """角球玩法:总角球 O/U、球队角球 O/U、角球单双、首角球队。
    近似:总角球 ~ Poisson(lc_home+lc_away),各队 ~ Poisson(lc_team)。半场角球无数据,不出。"""
    L = lc_home + lc_away
    ptot = [_pois_big(k, L) for k in range(N)]
    def over(line): return sum(ptot[k] for k in range(N) if k > line)
    odd = sum(ptot[k] for k in range(N) if k % 2)
    ph = [_pois_big(k, lc_home) for k in range(N)]
    pa = [_pois_big(k, lc_away) for k in range(N)]
    def team_over(pl, line): return sum(pl[k] for k in range(N) if k > line)
    return {
        "expected_corners": {"home": round(lc_home, 2), "away": round(lc_away, 2), "total": round(L, 2)},
        "corners_total": {str(l): {"line": l, "over": over(l), "under": 1 - over(l)} for l in total_lines},
        "corners_odd_even": {"odd": odd, "even": 1 - odd},
        "corners_team_home": {str(l): {"line": l, "over": team_over(ph, l), "under": 1 - team_over(ph, l)} for l in team_lines},
        "corners_team_away": {str(l): {"line": l, "over": team_over(pa, l), "under": 1 - team_over(pa, l)} for l in team_lines},
        "first_corner": {"home": lc_home / L, "away": lc_away / L} if L > 0 else {"home": 0.5, "away": 0.5},
    }


def mg2(dist, lo, hi):
    return sum(v for k, v in dist.items() if lo <= k <= hi)


def _res(i, j):
    return "home" if i > j else ("draw" if i == j else "away")


def _combo(P, res, btts_yes):
    s = 0.0
    for i in range(len(P)):
        for j in range(len(P)):
            if _res(i, j) == res and ((i > 0 and j > 0) == btts_yes):
                s += P[i][j]
    return s


def _combo_ou(P, res, line, over):
    s = 0.0
    for i in range(len(P)):
        for j in range(len(P)):
            if _res(i, j) == res and ((i + j > line) == over):
                s += P[i][j]
    return s
