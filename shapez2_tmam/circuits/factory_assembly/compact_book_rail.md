# 486 道混合车环线和配料场

每九道配一组双环。基础料车由北侧按地址递增卸货，结晶车由南侧按地址递减卸货。两类车分别经过自己的配料台和车库合流，再回到首站。首组原生样件包含工道页、两条闭合环线和配料场。配料场接单料车的来车与空车回程轨。整册 54 组共 108 条混合车环线。

| 路线 | 车厢配置 | 供料方式 |
|---|---|---|
| 基础料 | `q2、q3、q1、q0` 四组，每组三节 | 前两节形状车各装 `C/R/S`、`W/空/空`，第三节液体车自底向上装红、绿、蓝 |
| 结晶 | 一节液体车 | 自底向上装红、绿、蓝 |
| 单料 | 一节形状或液体车，底层供换装 | 每辆只载一种整片或原色，从相应 `raw_banks` 来轨进站，卸入四条独立带或管，经去轨回原料场 |

## 导入和重导

已有工道页时只导入 `compact-book-rail-overlay.spz2bp`。从空地搭建首组时导入 `compact-book-rail-page.spz2bp`，该蓝图已包含工道页和运输覆盖件。共用配方控制仍用 486 道册里的 `controls.spz2bp`。

整册铺设表中 `groups[].place_at` 是工段页原点。`route_templates` 内轨道、站场和回程都使用相对原点坐标。将其 X 加上对应页的 `place_at[0]`，Y 与岛层沿用模板。各组相隔 108 个岛格。`factory_stop_addresses` 给出实际停靠顺序。配料端的 `raw_banks[].single_track` 给出每种原料的来去轨。`transfers` 给出停靠车头、卸货座、混合车装货座、目标车厢层和四个通道行号。

```sh
python -m shapez2_tmam.circuits.factory_assembly.compact_book_rail --output-prefix compact-book-rail
python -m shapez2_tmam.circuits.factory_assembly.compact_book_rail --page 53 --origin-x 37 --output-prefix compact-book-rail-final
```

回程分别从相对坐标 `(36, -58, 0)`、`(60, 69, 0)` 汇入配料来轨，车库从同一合流的直行支路发车。轨道类型和端口按本机 `SPZGameAssembly.dll` 的 `TrainNavigationIslandDefinitionFactory.CreateRailDefinitions`，颜色配置按 `RailConfiguration.Sync`。样件原生解码已逐格核对发车支路、环线方向、九道两类卸货站和单料车外接轨。首组覆盖件共 31 块换装平台，合装共 292 块大平台。

## 一满带车队和原料开单

默认成品带速每秒 2 件，计划同站每 60 秒到货，示例回程 120 秒。每条有需求的路线至少配置两辆轮转车，前提是单次有效载量达到表内需求。基础料上界按九道最多七个基础操作算。九道入口最多带入六份活槽，基础操作每次加一份，二元操作每次归并一份。结晶按九道均消耗染料预留。

| 混合车层 | 九道每层峰值 | 60 秒有效装载需求 |
|---|---:|---:|
| 基础料形状 | 14 件/秒 | 840 件 |
| 基础料红，含制针 | 280 L/s | 16,800 L |
| 基础料绿或蓝 | 140 L/s | 8,400 L |
| 结晶任一原色 | 360 L/s | 21,600 L |

基础料单料车按四个同货种目标车层合计开单。每种整片最多每秒 56 件，制针红最多 1,120 L/s，绿或蓝各最多 560 L/s；各颜色和各车层独立取峰值。`raw_orders` 同时列出通用峰值和实际冻结订单，样件默认计算 145 道悬空目标。`--recipe` 可换成带 `target`、`instructions` 的固定配方。`fixed_stop_loads` 给出该单每站、每车层和卸货行的最低有效到货量。

填入实测混合车每层有效载量和单料车底层有效载量后，导出会用 `--mixed-shape-payload`、`--mixed-fluid-payload`、`--raw-shape-payload`、`--raw-fluid-payload` 分别计算发车需求。每分钟有效趟数取 `max(60 / 到站间隔, 60 × 每秒需求 / 有效载量)`。乘实测周转秒数再除以 60 后向上取整，得到该路车辆数下界。混合车取各装载层中最大的车辆数。实机放行前尤其核对首站卸货之后，末站仍达到 `fixed_stop_loads` 所列下限。载量、站间分配和持续满带由 #72 记录。
