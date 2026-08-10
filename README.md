# FG-football-prediction

**中文** · ForeGate 足球赛事预测框架。一套 **Dixon-Coles 进球分布引擎** 覆盖单场足球全部主流玩法,覆盖平台全部 55 个足球联赛(另含更多杯赛/洲际赛/国家队,共 100+ 赛事)。零依赖、秒级响应。

**English** · ForeGate football match-prediction framework — one **Dixon-Coles goal-distribution engine** producing all major single-match markets across the platform's 55 football leagues (100+ competitions in total). Zero-dependency, millisecond responses.

> **免责声明 / Disclaimer** — 盘前统计估计,不构成投注或投资建议。Pre-match statistical estimate; not betting or investment advice.

---

## 核心思路 / Core idea

`评级(攻防) → 期望进球 (λ_home, λ_away) → 比分概率矩阵 → 全部玩法`

每队有**攻击力/防守力**评级 + **主场优势**,算出双方期望进球,展开为泊松比分矩阵(含 Dixon-Coles 低比分修正),所有进球类玩法在矩阵上求和;半场玩法按实测占比(≈0.458)拆两个半场泊松;角球玩法用独立角球攻防评级。

## HTTP API

```
GET /predict?categoryId=82&a=Arsenal&b=Chelsea[&lang=zh|en|vi][&oh=&od=&oa=]
```
赛事解析三选一:`categoryId`(内部分类 id)/ `code`(league_id)/ `name`。队名支持**模糊匹配**(精确→子串→词级+缩写扩展)。传 `oh/od/oa`(1X2 欧赔)则附盘口去水隐含概率 `market` + 分歧 `divergence`。
其它:`GET /health`、`GET /competitions`、`GET /teams?categoryId=..&q=..`。

**返回顶层字段**:`code, competition, category_id, pool, A, B, lang, matched_exact, markets, reasons`(传赔率另有 `market, divergence`)。

---

## 支持的玩法字段 / Market fields(`markets` 内,概率均 0–1)

### 全场进球类 / Full-time goals(所有赛事)
| 字段 | 含义 | 值 |
|---|---|---|
| `expected_goals` | 双方期望进球 | home, away |
| `one_x_two` | 胜平负 | home, draw, away |
| `double_chance` | 双胜 | 1X, 12, X2 |
| `dnb` | 单外(平局退款) | home, away |
| `over_under` | 大小球(多线) | 0.5/1.5/2.5/3.5/4.5 → line, over, under |
| `handicap` | 让球(亚洲让球,0.5 步长) | -3.5/-2.5/-1.5/-0.5/+0.5/+1.5/+2.5/+3.5 → line, home, away (push 恒为 0,亚洲盘无走盘) |
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

### 半场类 / Half-time(所有赛事)
| 字段 | 含义 | 值 |
|---|---|---|
| `first_half` / `second_half` | 上/下半场 | result{home,draw,away} + over_under{0.5/1.5/2.5} + btts{yes,no} |
| `ht_result` | 半场胜平负 | home, draw, away |
| `highest_scoring_half` | 最高进球半场 | first, equal, second |
| `neither_score_first` | 谁都不先进球(全场0-0) | yes, no |

### 角球类 / Corners(20 联赛,见下表 ✅)
| 字段 | 含义 | 值 |
|---|---|---|
| `expected_corners` | 期望角球 | home, away, total |
| `corners_total` | 总角球大小 | 8.5..12.5 → line, over, under |
| `corners_odd_even` | 角球单双 | odd, even |
| `corners_team_home` / `corners_team_away` | 球队角球大小 | 3.5/4.5/5.5 → line, over, under |
| `first_corner` | 首角球队 | home, away |

**做不了(数据缺口)**:半场角球、球员盘(射手/进球数)、牌数盘、低级别联赛角球。

-
---

## 平台玩法字段对齐 / Platform market keys(`platform_markets`)

预测返回额外含 `platform_markets`,直接用**平台玩法 key** 暴露,前端可按 key 直取:

| 平台 key | 值 | 内部来源 |
|---|---|---|
| `moneyline` | home, draw, away | one_x_two |
| `spreads` | 多条 {line, home, away} (push 恒为 0) | handicap |
| `totals` | 多条 {line, over, under} | over_under |
| `both_teams_to_score` | yes, no | btts |
| `soccer_exact_score` | [[比分, 概率], ...] | correct_score |
| `soccer_team_totals` | home / away → {line, over, under} | team_total_* |
| `total_corners` | 多条 {line, over, under}(仅角球覆盖联赛) | corners_total |
| `soccer_first_to_score` | home, away, none(谁先进球 / 无进球) | 由 λ 推导 |
| `soccer_team_to_advance` | home, away(**仅淘汰赛**,联赛为 null) | 由胜平负单场晋级近似 |
| `soccer_penalty_shootout` | yes, no(**仅淘汰赛**,联赛为 null) | 由平局概率近似 |

> `soccer_team_to_advance` / `soccer_penalty_shootout` 只对杯赛/淘汰赛输出概率,联赛比赛该两项为 `null`(不适用)。
> These two are populated only for knockout competitions; for league matches they are `null`.


---

## 覆盖的赛事 / Competitions

仓库共建有 100+ 赛事评级快照。其中**平台足球 55 个联赛全部覆盖**,均可用 `platform_id`(前端内部联赛 id)直接解析调用。下表 `code` = 内部目录名(games/&lt;code&gt;),`角球` ✅ 表示额外支持角球玩法。

The repo holds 100+ competition snapshots. **All 55 platform football leagues are covered** and resolvable by `platform_id`. Below, `code` = internal directory (games/&lt;code&gt;); `角球` ✅ = corner markets also available.

| platform_id | 联赛 | code(af_id) | 角球 |
|---|---|---|:--:|
| 30113 | UCL | 2 | — |
| 30114 | Copa Sudamericana | 11 | — |
| 30115 | Copa Libertadores | 13 | — |
| 30116 | EFL Championship | 40 | ✅ |
| 30117 | MLS | 253 | ✅ |
| 30118 | EPL | 39 | ✅ |
| 30119 | Liga MX | 262 | ✅ |
| 30120 | Brazil Serie B | 72 | — |
| 30121 | Super Lig (Turkey) | 203 | — |
| 30122 | Colombia Primera A | 239 | — |
| 30123 | Chinese Super League | 169 | ✅ |
| 30124 | J2 League | 99 | — |
| 30125 | Saudi Professional League | 307 | ✅ |
| 30126 | La Liga | 140 | ✅ |
| 30127 | Czechia Fortuna Liga | 345 | — |
| 30128 | Japan J League | 98 | ✅ |
| 30129 | A League Soccer | 188 | ✅ |
| 30130 | Bundesliga | 78 | ✅ |
| 30131 | Norway Eliteserien | 103 | — |
| 30132 | Eredivisie | 88 | ✅ |
| 30133 | Denmark Superliga | 119 | — |
| 30134 | K League | 292 | ✅ |
| 30135 | Serie A | 135 | ✅ |
| 30136 | Ligue 1 | 61 | ✅ |
| 30137 | La Liga 2 | 141 | ✅ |
| 30138 | UEL | 3 | — |
| 30139 | Ligue 2 | 62 | — |
| 30140 | Serie B (Italy) | 136 | — |
| 30141 | Primeira Liga | 94 | ✅ |
| 30142 | UEFA Europa Conference League | 848 | — |
| 30143 | 2. Bundesliga | 79 | ✅ |
| 30144 | Morocco Botola Pro | 200 | — |
| 30145 | Egypt Premier League | 233 | — |
| 30146 | Brazil Serie A | 71 | ✅ |
| 30147 | Romania Superliga | 283 | — |
| 30148 | Copa Del Rey | 143 | — |
| 30149 | CoppaItalia | 137 | — |
| 30151 | Chile Primera | 265 | — |
| 30152 | Coupe De France | 66 | — |
| 30153 | FIFA World Cup | 1 | — |
| 30154 | Peru Liga 1 | 281 | — |
| 30155 | Bolivia LFPB | 344 | — |
| 30156 | EFL Cup | 48 | — |
| 30194 | Taça de Portugal | 96 | — |
| 30195 | Copa do Brasil | 73 | — |
| 30196 | DFB-Pokal | 81 | — |
| 30197 | Women's Champions League | 525 | — |
| 30198 | FA Cup | 45 | — |
| 30199 | CONCACAF Champions Cup | 16 | — |
| 30200 | Primera División Argentina | 128 | ✅ |
| 30202 | FIFA Friendly | 10 | — |
| 30208 | UEFA Women's WC Qualifiers | 880 | — |
| 30222 | Allsvenskan | 113 | — |
| 30223 | Liga de Primera (Nicaragua) | 396 | — |
| 30224 | Australia Cup | 874 | — |


---

## 数据 / Data
- 进球:API-Football,主流联赛 2012–2025(平均每联赛 6.7 季)。
- 角球:欧洲 11 联赛(football-data.co.uk,2018–2025)+ 非欧 9 联赛(API-Football,2024–2025)。

## 目录 / Layout
```
core/ratings.py  markets.py  odds.py  backtest.py  predict.py
games/<code>/config.json  ratings.json  (corners_ratings.json)
cli.py  server.py  refresh.py  render.yaml
```

## 部署 / Deploy
Render → New → Blueprint 连接本仓库(读 render.yaml,免费档)。每日刷新 .github/workflows/daily-refresh.yml 增量续训,需配置 Secret `APIFOOTBALL_KEY`。

## License
MIT
