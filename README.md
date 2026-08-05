# FG-football-prediction

**中文** · ForeGate 足球赛事预测框架。一套 **Dixon-Coles 进球分布引擎** 覆盖单场足球全部主流玩法,覆盖全球 83 项赛事(联赛/杯赛/洲际赛/国家队)。零依赖、秒级响应。

**English** · ForeGate football match-prediction framework — one **Dixon-Coles goal-distribution engine** producing all major single-match markets across 83 competitions. Zero-dependency, millisecond responses.

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

---

## 覆盖的赛事 / Competitions(83)

> `categoryId`=内部分类 id(前端传参键);`code`=API-Football league_id;`角球`✅ 表示支持角球玩法。

### 联赛 / Leagues(55)

| categoryId | 名称 Name | 国家/地区 | code | 角球 |
|---|---|---|---|:--:|
| 102561 | Liga Profesional Argentina | Argentina | 128 | ✅ |
| 105240 | Primera Nacional | Argentina | 129 | — |
| 102765 | A-League | Australia | 188 | ✅ |
| 104929 | Bundesliga | Austria | 218 | — |
| 102648 | Serie A | Brazil | 71 | ✅ |
| 104936 | First League | Bulgaria | 172 | — |
| 105261 | Primera B | Chile | 266 | — |
| 105259 | League One | China | 170 | — |
| 102764 | Super League | China | 169 | ✅ |
| 105260 | Primera B | Colombia | 240 | — |
| 104318 | Primera División | Costa-Rica | 162 | — |
| 102652 | Superliga | Denmark | 119 | — |
| 105242 | Liga Pro | Ecuador | 242 | — |
| 102643 | Championship | England | 40 | ✅ |
| 104319 | League One | England | 41 | — |
| 82 | Premier League | England | 39 | ✅ |
| 105243 | Veikkausliiga | Finland | 244 | — |
| 102070 | Ligue 1 | France | 61 | ✅ |
| 102864 | 2. Bundesliga | Germany | 79 | ✅ |
| 1494 | Bundesliga | Germany | 78 | ✅ |
| 104322 | Liga Nacional | Guatemala | 339 | — |
| 104933 | NB I | Hungary | 271 | — |
| 105244 | Úrvalsdeild | Iceland | 164 | — |
| 103986 | Indian Super League | India | 323 | — |
| 105245 | Premier Division | Ireland | 357 | — |
| 100618 | Serie A | Italy | 135 | ✅ |
| 102649 | J1 League | Japan | 98 | ✅ |
| 102770 | J2 League | Japan | 99 | — |
| 105246 | Premier League | Kazakhstan | 389 | — |
| 105253 | Virsliga | Latvia | 365 | — |
| 105254 | A Lyga | Lithuania | 362 | — |
| 102448 | Liga MX | Mexico | 262 | ✅ |
| 101735 | Eredivisie | Netherlands | 88 | ✅ |
| 105250 | 1. Division | Norway | 104 | — |
| 102651 | Eliteserien | Norway | 103 | — |
| 105705 | Ekstraklasa | Poland | 106 | — |
| 102122 | Primeira Liga | Portugal | 94 | ✅ |
| 102593 | Premier League | Russia | 235 | — |
| 102650 | Pro League | Saudi-Arabia | 307 | ✅ |
| 102872 | Premiership | Scotland | 179 | ✅ |
| 104932 | Super Liga | Serbia | 286 | — |
| 104934 | 1. SNL | Slovenia | 373 | — |
| 105734 | Premier Soccer League | South-Africa | 288 | — |
| 102771 | K League 1 | South-Korea | 292 | ✅ |
| 105258 | K League 2 | South-Korea | 293 | — |
| 780 | La Liga | Spain | 140 | ✅ |
| 102866 | Segunda División | Spain | 141 | ✅ |
| 104930 | Allsvenskan | Sweden | 113 | — |
| 105251 | Superettan | Sweden | 114 | — |
| 105704 | Super League | Switzerland | 207 | — |
| 100100 | Major League Soccer | USA | 253 | ✅ |
| 103886 | Premier League | Ukraine | 333 | — |
| 105241 | Primera División - Apertura | Uruguay | 268 | — |
| 105247 | Super League | Uzbekistan | 369 | — |
| 105249 | Primera División | Venezuela | 299 | — |

### 国内杯 / Domestic Cups(9)

| categoryId | 名称 Name | 国家/地区 | code | 角球 |
|---|---|---|---|:--:|
| 104336 | Australia Cup | Australia | 874 | — |
| 104335 | Cup | Austria | 220 | — |
| 101807 | FA Cup | England | 45 | — |
| 101102 | League Cup | England | 48 | — |
| 102604 | Coupe de France | France | 66 | — |
| 102154 | DFB Pokal | Germany | 81 | — |
| 104334 | Taça de Portugal | Portugal | 96 | — |
| 105706 | League Cup | Scotland | 185 | — |
| 101783 | Copa del Rey | Spain | 143 | — |

### 洲际俱乐部 / Continental Club(8)

| categoryId | 名称 Name | 国家/地区 | code | 角球 |
|---|---|---|---|:--:|
| 102562 | CONMEBOL Libertadores | World | 13 | — |
| 102563 | CONMEBOL Sudamericana | World | 11 | — |
| 102192 | FIFA Club World Cup | World | 15 | — |
| 102449 | Leagues Cup | World | 772 | — |
| 1234 | UEFA Champions League | World | 2 | — |
| 103885 | UEFA Champions League Women | World | 525 | — |
| 102763 | UEFA Europa Conference League | World | 848 | — |
| 100626 | UEFA Europa League | World | 3 | — |

### 国家队 / National Teams(11)

| categoryId | 名称 Name | 国家/地区 | code | 角球 |
|---|---|---|---|:--:|
| 102263 | CONCACAF Gold Cup | World | 22 | — |
| 100817 | Euro Championship | World | 4 | — |
| 102539 | Friendlies | World | 10 | — |
| 105795 | Friendlies Clubs | World | 667 | — |
| 102356 | UEFA Championship - Women | World | 743 | — |
| 100782 | UEFA Nations League | World | 5 | — |
| 102267 | UEFA U21 Championship | World | 38 | — |
| 102350 | World Cup | World | 1 | — |
| 102544 | World Cup - Qualification Europe | World | 32 | — |
| 101982 | World Cup - Qualification Intercontinental Play-offs | World | 37 | — |
| 105215 | World Cup - Women - Qualification Concacaf | World | 927 | — |

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
