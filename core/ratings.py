#!/usr/bin/env python3
"""进球强度评级(在线泊松攻防 + 主场优势 + 时间衰减近似)。
每队 攻击力 atk / 防守力 dfn;期望进球 λ_home=exp(mu+hfa+atk_h-dfn_a), λ_away=exp(mu+atk_a-dfn_h)。
在线 SGD 更新(近期比赛权重更高由学习率体现),赛季边界可选向均值回归。
同一引擎服务三种评级池:联赛(单联赛)/ 跨联赛俱乐部(杯赛)/ 国家队。"""
import math
from collections import defaultdict


class PoissonRatings:
    def __init__(self, lg_goal=1.35, hfa=0.25, lr=0.03, season_reset=1.0):
        self.atk = defaultdict(float)
        self.dfn = defaultdict(float)
        self.mu = math.log(lg_goal)
        self.hfa = hfa
        self.lr = lr
        self.season_reset = season_reset  # <1.0 时,换季对评级做向均值收缩
        self._season = None
        self.gp = defaultdict(int); self.w = defaultdict(int); self.d = defaultdict(int); self.l = defaultdict(int)

    def rates(self, h, a):
        lh = math.exp(self.mu + self.hfa + self.atk[h] - self.dfn[a])
        la = math.exp(self.mu + self.atk[a] - self.dfn[h])
        return min(max(lh, 0.15), 6.0), min(max(la, 0.15), 6.0)

    def _newseason(self, s):
        if self._season is not None and s != self._season and self.season_reset < 1.0:
            for t in list(self.atk): self.atk[t] *= self.season_reset
            for t in list(self.dfn): self.dfn[t] *= self.season_reset
        self._season = s

    def update(self, h, a, hg, ag, season=None):
        if season is not None:
            self._newseason(season)
        lh, la = self.rates(h, a)
        eh, ea, lr = lh - hg, la - ag, self.lr
        self.atk[h] -= lr * eh; self.dfn[a] += lr * eh
        self.atk[a] -= lr * ea; self.dfn[h] += lr * ea
        self.hfa -= 0.002 * eh
        self.mu -= 0.0005 * (eh + ea)
        self.gp[h] += 1; self.gp[a] += 1
        if hg > ag: self.w[h] += 1; self.l[a] += 1
        elif hg < ag: self.w[a] += 1; self.l[h] += 1
        else: self.d[h] += 1; self.d[a] += 1

    def fit(self, matches):
        """matches: 已按时间升序的列表, 每项 {home,away,hg,ag,season?}"""
        for m in matches:
            self.update(m["home"], m["away"], m["hg"], m["ag"], m.get("season"))
        return self

    def snapshot(self):
        teams = {}
        for t in self.gp:
            teams[t] = {"atk": round(self.atk[t], 5), "dfn": round(self.dfn[t], 5),
                        "w": self.w[t], "d": self.d[t], "l": self.l[t], "gp": self.gp[t]}
        return {"mu": round(self.mu, 5), "hfa": round(self.hfa, 5), "teams": teams}

    @staticmethod
    def rates_from_snapshot(snap, h, a):
        mu, hfa, T = snap["mu"], snap["hfa"], snap["teams"]
        ah = T.get(h, {}).get("atk", 0.0); dh = T.get(h, {}).get("dfn", 0.0)
        aa = T.get(a, {}).get("atk", 0.0); da = T.get(a, {}).get("dfn", 0.0)
        lh = math.exp(mu + hfa + ah - da)
        la = math.exp(mu + aa - dh)
        return min(max(lh, 0.15), 6.0), min(max(la, 0.15), 6.0)
