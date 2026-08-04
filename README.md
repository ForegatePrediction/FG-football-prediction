# FG-football-prediction

ForeGate 足球赛事预测框架。一套 **Dixon-Coles 进球分布引擎** 产出全部玩法(1X2 / 双胜 / 单外 / 让球 / 大小球 / BTTS / 正确比分),覆盖 Polymarket 足球全量赛事(~83 个),按三类评级池组织:联赛 / 跨联赛俱乐部 / 国家队。

> 盘前统计估计,不构成投注建议。

## 核心思路

`评级(攻防) → 期望进球 (λ_home, λ_away) → 比分矩阵 → 全部玩法`。
足球盘口高效,回测显示收盘赔率(~56%)优于纯模型(~53%),故**不融合成单值**,而是对外**混合展示:模型概率 + 盘口去水隐含概率 + 分歧**(见 `core/odds.py`)。

## 数据源

- 赛果:**API-Football**(需 `APIFOOTBALL_KEY` 环境变量)。
- 赔率(线上混合展示用):API-Football 赛前赔率。历史赔率回测用 football-data.co.uk。

## 目录

```
core/ratings.py    在线泊松攻防评级(可服务联赛/俱乐部/国家队三种池)
core/markets.py    比分矩阵 -> 全玩法(含 Dixon-Coles 低比分修正)
core/odds.py       Shin 去水 + 分歧(混合展示)
core/backtest.py   走查式回测
core/predict.py    读快照零训练预测(模型 + 可选盘口双口径 + 三语理由)
games/<af_id>/     每个赛事:config.json / ratings.json / data/(gitignore)
cli.py  server.py
```

## 用法

```bash
python3 cli.py snapshot 39            # 由 games/39/data/matches.json 重建英超快照
python3 cli.py backtest 39            # 走查回测
python3 cli.py predict  39 "Arsenal" "Chelsea"
python3 server.py                     # HTTP API(PORT 默认 8000)
```

`code` = API-Football league_id;API 也支持 `categoryId`(Polymarket 标签 id)/ `name` 解析。

## 建模池

- **A 联赛(~55)**:每联赛独立评级。
- **B 国内杯 / C 洲际俱乐部赛(~17)**:跨联赛统一俱乐部评级池。
- **D 国家队 / 国际赛(~11)**:国家队评级池。

赛事↔league_id↔池 见 `足球赛事-映射表.md`。

## License

MIT
