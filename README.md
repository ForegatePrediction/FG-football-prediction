# FG-football-prediction

**中文** · ForeGate 足球赛事预测框架。一套 **Dixon-Coles 进球分布引擎** 覆盖单场足球全部主流玩法,保存 100 个赛事的历史模型;实时可更新覆盖以 `free-sources.json` 和 `refresh-state.json` 为准。零依赖、秒级响应。

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
| `handicap` | 让球(亚洲让球,0.5 步长,无走盘) | -3.5/-2.5/-1.5/-0.5/+0.5/+1.5/+2.5/+3.5 → line, home, away |
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
| `spreads` | 多条 {line, home, away} | handicap |
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

仓库保留 100 个赛事配置及历史模型。下表是接口映射，不代表全部仍在更新；免费源接入范围见 `free-sources.json`，实际源赛事日期见 `refresh-state.json`。均可用 `platform_id`(前端内部联赛 id)直接解析调用。下表 `code` = 内部目录名(games/&lt;code&gt;),`角球` ✅ 表示额外支持角球玩法。

Historical models remain available; live update coverage is recorded in `free-sources.json` and `refresh-state.json`. Competitions resolve by `platform_id`. Below, `code` = internal directory (games/&lt;code&gt;); `角球` ✅ = corner markets also available.

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
Render → New → Blueprint 连接本仓库(读 render.yaml,免费档)。每日北京时间 15:20（07:20 UTC）由 `.github/workflows/daily-refresh.yml` 从免费 ESPN 完赛赛果增量续训，无需密钥。

`python3 refresh.py --max-days 0` 补齐全部历史缺口；默认每批 31 天。独立联赛和杯赛引用的 `_clubpool` / `_natpool` 同时更新。仅采纳 90 分钟 FT，排除含加时/点球的最终比分。HTTP 失败、缺失比赛列表、达到分页上限均报错，成功前不推进日期游标。`refresh-state.json` 区分实际赛事日期与检查日期；未接入免费源的原联赛保留历史，不宣称持续更新。角球快照仍是历史数据，本次免费赛果更新不刷新角球模型。

## License
MIT

## 换源时的球队身份

`team-aliases.json` 将 64 个已核对的 ESPN 球队 ID 对齐已有模型名称，覆盖 MLS、沙特、中超、日职、巴西、阿根廷、葡超、荷甲、土超和苏超的命名差异。训练不使用预测接口的宽松模糊匹配。女足使用独立身份前缀。

命名修复以换源前模型为起点，在临时副本按相同比赛顺序重新计算换源增量。`source-migration-validation.json` 记录 74 个快照的验证：比赛总数、最新日期、累计更新数、最后一天已应用的比赛 ID 均不变，修复不丢弃赛果。

部分中超更名核对来源：[辽宁沈阳城市→辽宁铁人](https://www.thecfa.cn/lstz/20240206/33697.html)、[大连智行→大连英博](https://www.thecfa.cn/lstz/20240129/33637.html)、[青岛青春岛→青岛西海岸](https://www.thecfa.cn/qttz/20230308/32363.html)、[四川九牛→深圳新鹏城](https://www.thecfa.cn/lstz/20240206/33699.html)。

## VPS 与 GitHub 双通道更新

新增可选持久数据模式：设置 `FG_DATA_DIR` 后，预测从该目录的版本快照读取评分，赛事配置仍使用代码版本。数据目录缺失或不兼容时明确报错；通过原子切换 `current` 可更新评分，无需重启服务。未设置时保留仓库快照模式。

GitHub 每日任务将通过校验的数据包写入独立 `data-snapshots` 分支，包含评分、采集状态和文件哈希，不包含原始缓存、Token 或源代码。只有 VPS 迁移通过后才设置仓库变量 `DUAL_CHANNEL_DATA=true`：启用后 GitHub 使用自己的数据检查点续抓，并停止每日向主分支提交数据。未启用时保留原有主分支更新，避免迁移中断。

VPS 和 GitHub 独立采集、保存各自缓存与游标，生产只由 VPS 发布；GitHub 备份不会自动覆盖生产。安装、时间表、验证和人工恢复见[网关部署说明](https://github.com/ForegatePrediction/FG-prediction-gateway-v2/blob/main/deploy/DUAL_CHANNEL.md)。
