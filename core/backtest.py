#!/usr/bin/env python3
"""走查式回测:按时间处理,样本外(burn 之后)边预测边更新。
指标:1X2 命中 / 大小球命中 / Brier / LogLoss。"""
import math
from .ratings import PoissonRatings
from .markets import markets


def walk_forward(matches, burn_season, rho=-0.06, lg_goal=1.35, lr=0.03, season_reset=1.0):
    matches = sorted(matches, key=lambda m: (m["date"], m["home"]))
    R = PoissonRatings(lg_goal=lg_goal, lr=lr, season_reset=season_reset)
    n = hit = ouhit = 0
    brier = ll = 0.0
    for m in matches:
        h, a, hg, ag, s = m["home"], m["away"], m["hg"], m["ag"], m.get("season")
        if s is not None and s >= burn_season:
            lh, la = R.rates(h, a)
            mk = markets(lh, la, rho)
            o = mk["one_x_two"]; probs = [o["home"], o["draw"], o["away"]]
            out = 0 if hg > ag else (1 if hg == ag else 2)
            hit += (probs.index(max(probs)) == out); n += 1
            for k in range(3):
                brier += (probs[k] - (1 if out == k else 0)) ** 2
            ll += -math.log(max(probs[out], 1e-9))
            ouhit += ((mk["over_under"]["2.5"]["over"] >= 0.5) == (1 if hg + ag > 2.5 else 0))
        R.update(h, a, hg, ag, s)
    if not n:
        return {"N": 0}
    return {"N": n, "acc_1x2": hit / n, "acc_ou": ouhit / n, "brier": brier / n, "logloss": ll / n}
