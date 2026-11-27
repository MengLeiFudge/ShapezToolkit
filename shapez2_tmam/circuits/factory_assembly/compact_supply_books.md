# 486 道配料端装配三册

同一份 `rail-overlay.spz2bp` 与 53 张续接页和成品末页共用。导入工道页后，用 `index.json` 内同页 `place_at` 对准铁路覆盖件的局部原点。默认整册首组原点为 `(0, 0, 0)`，末组为 `(5724, 0, 0)`。末页成品带在 `(5826, 0, 0)` 平台东侧第 31 行。

| 分册 | 原生蓝图 | 装配位置 |
|---|---|---|
| 单料车 | `single-arrivals.spz2bp` | 按各页 `place_at` 放入 10 组卸货轨。每组从 `raw_banks` 找来车和空车回程口 |
| 单料车 | `single-shape-loading.spz2bp`、`single-fluid-loading.spz2bp` 及同类 `-depot.spz2bp` | 放在原料场。每辆车的第一节车厢只在底层装一种原料，通过装车板西侧 28～31 行接四条同料带或管 |
| 四角基础料与结晶换装 | `mixed-transfers.spz2bp` | 按同一页 `place_at` 放置。31 块台把单料车底层接到对应混合车车厢层 |
| 混合车回圈 | `mixed-loops.spz2bp` | 按同一页 `place_at` 放置。北环接四角基础料，南环接结晶，含混合车配料停车位、车库和回程合流 |

整组也可直接导入合装件 `rail-overlay.spz2bp`。上述三份页内分件叠放占位与合装件一致。单料车装车件和车库按矿点、染料源的实际位置放置。

## 重导

先准备包含 54 页的工道册，再执行配料端入口。工道册的原点、目标带速和到站间隔随册读取。导出器逐页核对真实卸货站轨位、四角与结晶的来去轨、页间六槽接续和末页一条成品带。

```sh
python -m shapez2_tmam.circuits.factory_assembly.compact_book --output-dir compact-book-486
python -m shapez2_tmam.circuits.factory_assembly.compact_supply_books --factory-book compact-book-486 --output-dir compact-supply-486
```

默认按 145 道悬空目标生成配料单。用 `--recipe 配方.json` 换单，文件包含 `target` 和六字段 `instructions`。`index.json` 的 `groups[].routes[]` 列出停靠顺序、混合车逐层装料、单料车开单与固定订单的逐站卸货行。装车件的 `source_kits` 接点为局部坐标。装车轨的来去轨和车库出口都是北向，按照原料场位置接到配料端的原料来轨，并把空车去轨接回原料场。

站名和线路仍在游戏内配置。索引给出线路名、卸货站名、混合车装货站名和单料车来站前缀。一个原料来站有多个车头时，按目标车厢号在前缀后加 `-Wxx`。依据开单和实测到站间隔安排发车。默认车队数量沿用 120 秒周转估算，实机卸量和持续满带由 #72 记录。
