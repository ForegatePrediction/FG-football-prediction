#!/usr/bin/env python3
"""统一命令行:snapshot / predict / backtest / list。
用法:
  python3 cli.py snapshot <code>              # 由 games/<code>/data/matches.json 重建 ratings.json
  python3 cli.py predict  <code> "A" "B"       # 预测全玩法
  python3 cli.py backtest <code>               # 走查回测
  python3 cli.py list     <code> <关键词>       # 查队伍
code = API-Football league_id(即 games/ 下的目录名)。"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.ratings import PoissonRatings
from core import backtest as bt
from core.predict import predict, list_teams

ROOT = os.path.dirname(os.path.abspath(__file__))


def _matches(code):
    f = os.path.join(ROOT, "games", str(code), "data", "matches.json")
    return sorted(json.load(open(f, encoding="utf-8")), key=lambda m: (m["date"], m["home"]))


def _cfg(code):
    return json.load(open(os.path.join(ROOT, "games", str(code), "config.json"), encoding="utf-8"))


def cmd_snapshot(code):
    cfg = _cfg(code); ms = _matches(code)
    R = PoissonRatings(lg_goal=cfg.get("lg_goal", 1.35), lr=cfg.get("lr", 0.03),
                       season_reset=cfg.get("season_reset", 1.0)).fit(ms)
    snap = R.snapshot()
    snap["updated_from"] = len(ms)
    p = os.path.join(ROOT, "games", str(code), "ratings.json")
    json.dump(snap, open(p, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"[{code}] {cfg.get('name')}: 拟合 {len(ms)} 场,{len(snap['teams'])} 支队,快照已写")


def cmd_backtest(code):
    cfg = _cfg(code); ms = _matches(code)
    seasons = sorted({m["season"] for m in ms if m.get("season") is not None})
    burn = cfg.get("burn_season") or (seasons[len(seasons) // 2] if seasons else 0)
    r = bt.walk_forward(ms, burn, rho=cfg.get("rho", -0.06),
                        lg_goal=cfg.get("lg_goal", 1.35), lr=cfg.get("lr", 0.03),
                        season_reset=cfg.get("season_reset", 1.0))
    if r.get("N"):
        print(f"[{code}] {cfg.get('name')} 样本外(>= {burn}): "
              f"1X2={r['acc_1x2']*100:.1f}%  大小球={r['acc_ou']*100:.1f}%  "
              f"Brier={r['brier']:.3f}  LogLoss={r['logloss']:.3f}  N={r['N']}")
    else:
        print(f"[{code}] 数据不足")


def cmd_predict(code, A, B):
    import argparse
    d = predict(code, A, B)
    print(json.dumps(d, ensure_ascii=False, indent=2))


def cmd_list(code, kw):
    for t, v in list_teams(code, kw)[:20]:
        print(f"  {t}  (W{v['w']} D{v['d']} L{v['l']}, {v['gp']}场)")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        print(__doc__); sys.exit()
    cmd = a[0]
    if cmd == "snapshot": cmd_snapshot(a[1])
    elif cmd == "backtest": cmd_backtest(a[1])
    elif cmd == "predict": cmd_predict(a[1], a[2], a[3])
    elif cmd == "list": cmd_list(a[1], a[2] if len(a) > 2 else "")
    else: print("未知命令", cmd)
