#!/usr/bin/env python3
"""由期望进球 (λ_home, λ_away) 生成比分矩阵,再推出全部足球玩法。
含 Dixon-Coles 低比分修正 rho。一套矩阵产出:1X2 / 双胜 / 单外(DNB) / 让球(亚盘) / 大小球 / BTTS / 正确比分。"""
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
    if rho:  # Dixon-Coles 低比分相关性修正
        tau = {(0, 0): 1 - lh * la * rho, (0, 1): 1 + lh * rho,
               (1, 0): 1 + la * rho, (1, 1): 1 - rho}
        for (i, j), f in tau.items():
            P[i][j] = max(P[i][j] * f, 0.0)
        s = sum(sum(r) for r in P)
        P = [[x / s for x in r] for r in P]
    return P


def markets(lh, la, rho=-0.06, total_line=2.5, hcap_line=0.0):
    P = score_matrix(lh, la, rho)
    N = len(P)
    home = draw = away = over = ah_home = ah_away = btts = 0.0
    scores = []
    for i in range(N):
        for j in range(N):
            p = P[i][j]
            if i > j: home += p
            elif i == j: draw += p
            else: away += p
            if i + j > total_line: over += p
            m = (i - j) + hcap_line
            if m > 0: ah_home += p
            elif m < 0: ah_away += p
            if i > 0 and j > 0: btts += p
            scores.append((i, j, p))
    scores.sort(key=lambda x: -x[2])
    denom = home + away or 1e-9
    return {
        "expected_goals": {"home": round(lh, 3), "away": round(la, 3)},
        "one_x_two": {"home": home, "draw": draw, "away": away},
        "double_chance": {"1X": home + draw, "12": home + away, "X2": draw + away},
        "dnb": {"home": home / denom, "away": away / denom},
        "over_under": {"line": total_line, "over": over, "under": 1 - over},
        "handicap": {"line": hcap_line, "home": ah_home, "away": ah_away},
        "btts": {"yes": btts, "no": 1 - btts},
        "correct_score": [(f"{i}-{j}", round(p, 4)) for i, j, p in scores[:6]],
    }
