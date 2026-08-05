# FG-football-prediction

**中文** · ForeGate 足球赛事预测框架。一套 **Dixon-Coles 进球分布引擎**,覆盖欧洲五大联赛(英超 / 西甲 / 意甲 / 德甲 / 法甲)单场全部主流玩法。数据全部来自免费公开源、**无需任何 API key**,零依赖、秒级响应。

**English** · ForeGate football match-prediction framework — one **Dixon-Coles goal-distribution engine** producing all major single-match markets for Europe's big five (Premier League / La Liga / Serie A / Bundesliga / Ligue 1). Data is entirely from a free public source, **no API key required**, zero-dependency, millisecond responses.

> **免责声明 / Disclaimer** — 盘前统计估计,不构成投注或投资建议。Pre-match statistical estimate; not betting or investment advice.

---

## 核心思路 / Core idea

`评级(攻防) → 期望进球 (λ_home, λ_away) → 比分概率矩阵 → 全部玩法`

每队有**攻击力/防守力**评级 + **主场优势**,算出双方期望进球,展开为泊松比分矩阵(含 Dixon-Coles 低比分修正),所有进球类玩法在矩阵上求和;半场玩法按实测占比(≈0.458)拆两个半场泊松;角球玩法用一套独立的角球攻防评级(同一引擎,喂角球数)。

Each team has attack/defense ratings plus home advantage → expected goals → a Poisson score matrix (with the Dixon-Coles low-score correction); every goal market is summed off that matrix. Half-time markets split into two half-Poissons by an empirical share (≈0.458); corners use a separate corner attack/defense rating (same engine, fed corner counts).

---

## 覆盖联赛 / Leagues (5)

`categoryId` = 平台分类 id(前端传参键);`code` = 内部联赛目录名;命中率 = 走查式样本外回测(burn-in 到 2019 赛季)。所有联赛均支持角球玩法。

| 联赛 League | 国家 | categoryId | code | 样本 Games | 1X2 | 大小球 O/U | 角球 |
|---|---|---|---|---|---|---|:--:|
| Premier League | England | 82 | 39 | 5,320 | 53.2% | 55.4% | ✅ |
| La Liga | Spain | 780 | 140 | 5,325 | 52.3% | 55.9% | ✅ |
| Serie A | Italy | 100618 | 135 | 5,320 | 53.5% | 55.3% | ✅ |
| Bundesliga | Germany | 1494 | 78 | 4,284 | 51.9% | 60.8% | ✅ |
| Ligue 1 | France | 102070 | 61 | 4,997 | 51.3% | 55.3% | ✅ |

> 历史深度:每个联赛覆盖近 14 个赛季(2012/13–2025/26),比分 / 半场 / 角球 / 赔率字段齐全。每日增量任务持续把新赛果并入评级。
> History: each league covers ~14 seasons (2012/13–2025/26) with full score / half-time / corner / odds fields. A daily incremental job keeps merging new results.

---

## HTTP API

```
GET /predict?categoryId=82&a=Arsenal&b=Chelsea[&lang=zh|en|vi][&oh=&od=&oa=]
```
赛事解析三选一:`categoryId`(内部分类 id)/ `code`(联赛目录名)/ `name`。队名支持**模糊匹配**(精确→子串→词级+缩写扩展)。传 `oh/od/oa`(1X2 欧赔)则附盘口去水隐含概率 `market` + 分歧 `divergence`(模型与市场分开展示,不融合)。
其它:`GET /health`、`GET /competitions`、`GET /teams?categoryId=..&q=..`。

**返回顶层字段**:`code, competition, category_id, A, B, lang, matched_exact, markets, reasons`(传赔率另有 `market, divergence`)。

---

## 支持的玩法字段 / Market fields(`markets` 内,概率均 0–1)

### 全场进球类 / Full-time goals
| 字段 | 含义 | 值 |
|---|---|---|
| `expected_goals` | 双方期望进球 | home, away |
| `one_x_two` | 胜平负 | home, draw, away |
| `double_chance` | 双胜 | 1X, 12, X2 |
| `dnb` | 单外(平局退款) | home, away |
| `over_under` | 大小球(多线) | 0.5/1.5/2.5/3.5/4.5 → line, over, under |
| `handicap` | 让球 | -2/-1/0/1/2 → line, home, away, push |
| `btts` | 双方进球 | yes, no |
| `correct_score` | 正确比分(前8) | [["2-1",0.10],...] |
| `exact_goals` | 精确总进球数 | 0..5, 6+ |
| `multigoals` | 进球区间 | 0-1, 2-3, 4-6, 7+ |
| `winning_margin` | 净胜球 | home_by_1/2/3+, draw, away_by_1/2/3+ |
| `odd_even` / `home_odd_even` / `away_odd_even` | 单双(总/主/客) | odd, even |
| `team_total_home` / `team_total_away` | 球队进球大小 | 0.5/1.5/2.5 → line, over, under |
| `team_score_home` / `team_score_away` | 球队是否进球 | yes, no |
| `team_2plus_home` / `team_2plus_away` | 球队两球+ | yes, no |
| `clean_sheet_home` / `clean_sheet_away` | 零封 | yes, no |
| `win_to_nil_home` / `win_to_nil_away` | 零封制胜 | yes, no |
| `result_btts` | 赛果+双方进球 | home_yes/no, draw_yes/no, away_yes/no |
| `result_ou25` | 赛果+大小2.5 | home_over/under, draw_..., away_... |

### 半场类 / Half-time
| 字段 | 含义 | 值 |
|---|---|---|
| `first_half` / `second_half` | 上/下半场 | result{home,draw,away} + over_under{0.5/1.5/2.5} + btts{yes,no} |
| `ht_result` | 半场胜平负 | home, draw, away |
| `highest_scoring_half` | 最高进球半场 | first, equal, second |
| `neither_score_first` | 谁都不先进球(全场0-0) | yes, no |

### 角球类 / Corners
| 字段 | 含义 | 值 |
|---|---|---|
| `expected_corners` | 期望角球 | home, away, total |
| `corners_total` | 总角球大小 | 8.5..12.5 → line, over, under |
| `corners_odd_even` | 角球单双 | odd, even |
| `corners_team_home` / `corners_team_away` | 球队角球大小 | 3.5/4.5/5.5 → line, over, under |
| `first_corner` | 首角球队 | home, away |

**做不了(数据缺口)**:半场角球、球员盘(射手/进球数)、牌数盘。

---

## 数据 / Data

全部来自 **football-data.co.uk** 免费公开 CSV(比分 + 半场比分 + 角球 + 赔率),近 14 个赛季,**无需任何 API key、零成本**。
All data from **football-data.co.uk** free public CSVs (scores + half-time + corners + odds), ~14 seasons, **no API key, zero cost**.

一次性全量重建:`python3 build.py`。 Full rebuild from scratch: `python3 build.py`.

## 目录 / Layout
```
core/    ratings.py  markets.py  odds.py  backtest.py  predict.py
games/<code>/  config.json  ratings.json  corners_ratings.json  data/{matches,corners}.json
cli.py  server.py  build.py  refresh.py  render.yaml
```

## 部署 / Deploy
Render → New → Blueprint 连接本仓库(读 `render.yaml`,免费档)。每日刷新 `.github/workflows/daily-refresh.yml` 从免费源增量续训——**无需配置任何 Secret**。
Render → New → Blueprint on this repo (reads `render.yaml`, free plan). The daily workflow refreshes from the free source — **no secrets to configure**.

## License
MIT
