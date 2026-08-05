# FG-football-prediction

**中文** ·
ForeGate 足球赛事预测框架。一套 **Dixon-Coles 进球分布引擎** 覆盖单场足球的全部主流玩法(胜平负 / 大小球 / 让球 / 双方进球 / 正确比分 / 半场类 / 角球…),覆盖全球 80+ 项赛事(联赛 / 杯赛 / 洲际赛 / 国家队)。零依赖、秒级响应。

**English** ·
ForeGate football match-prediction framework. A single **Dixon-Coles goal-distribution engine** produces all major single-match markets (1X2 / totals / handicap / BTTS / correct score / half-time markets / corners…) across 80+ competitions worldwide (leagues / domestic cups / continental cups / national teams). Zero-dependency, millisecond responses.

> **免责声明 / Disclaimer** — 盘前统计估计,不构成投注或投资建议。 Pre-match statistical estimates; not betting or investment advice.

---

## 核心思路 / Core idea

`评级(攻防) → 期望进球 (λ_home, λ_away) → 比分概率矩阵 → 全部玩法`

每支球队有 **攻击力 / 防守力** 评级 + **主场优势**,算出双方期望进球,再展开成泊松比分矩阵(含 Dixon-Coles 低比分修正);所有进球类玩法都在该矩阵上求和得到。半场玩法按实测占比拆分两个半场泊松;角球玩法用独立的角球攻防评级。

Each team carries **attack / defense** ratings plus **home advantage** → expected goals → a Poisson score matrix (with Dixon-Coles low-score correction). All goal markets are sums over that matrix. Half-time markets split each side's rate into two half Poissons; corner markets use a separate corner attack/defense model.

## 覆盖 / Coverage

- **80+ 赛事 / 80+ competitions**:55 联赛 + 9 国内杯 + 8 洲际赛 + 11 国家队/国际赛,按三种评级池组织(联赛 / 跨联赛俱乐部 / 国家队)。
- **进球历史 / goals history**:主流联赛 2012–2025;数据源 API-Football。
- **角球 / corners**:20 个主流联赛(欧洲 + 美洲/亚太头部)。

## 目录 / Layout

```
core/ratings.py    在线泊松攻防评级(联赛/俱乐部/国家队通用)
core/markets.py    比分矩阵 -> 全场/半场/角球玩法
core/odds.py       赔率去水 + 分歧(混合展示:模型概率 vs 盘口隐含)
core/backtest.py   走查式回测
core/predict.py    读快照零训练预测(三语理由 + 可选盘口双口径)
games/<code>/      每赛事:config.json / ratings.json / (corners_ratings.json)
cli.py  server.py  refresh.py
```

## HTTP API

```bash
python3 server.py            # PORT 默认 8000
```

| Endpoint | 说明 / Description |
|---|---|
| `GET /health` | 健康检查 |
| `GET /competitions` | 所有赛事 + categoryId |
| `GET /teams?categoryId=82&q=Arsenal` | 查队伍 / find teams |
| `GET /predict?categoryId=82&a=Arsenal&b=Chelsea` | 全部玩法 + 三语理由 |

`/predict` 赛事解析三选一:`categoryId`(内部分类 id)/ `code`(API-Football league_id)/ `name`。可选 `lang=zh|en|vi`;传 `oh/od/oa`(1X2 欧赔)则附盘口去水隐含概率 + 分歧。CORS 全开,前端直连。

Match resolution accepts one of `categoryId` / `code` / `name`. Optional `lang=zh|en|vi`; pass `oh/od/oa` (1X2 decimal odds) to attach market-implied probabilities and divergence.

## 用法 / Usage

```bash
python3 cli.py snapshot 39                  # 由数据重建英超快照
python3 cli.py backtest 39                  # 走查回测
python3 cli.py predict  39 "Arsenal" "Chelsea"
```

## 部署 / Deploy (Render free plan)

1. 推送到 GitHub;Render → New → Blueprint 连接本仓库(读 `render.yaml`)→ 一键部署。免费档闲置休眠,首个请求冷启动约 30–50 秒。
2. 每日刷新:`.github/workflows/daily-refresh.yml` 每日增量续训评级,需在仓库 Secrets 配置 `APIFOOTBALL_KEY`。

Push to GitHub, deploy on Render via `render.yaml`. Daily incremental refresh runs via GitHub Actions (set `APIFOOTBALL_KEY` secret).

## License

MIT
