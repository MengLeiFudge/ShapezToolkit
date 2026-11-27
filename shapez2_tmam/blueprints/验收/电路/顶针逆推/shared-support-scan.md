# 共用 K/G 支撑扫描

S 筛选、Pin 静止定位和递归 G 共用一件 `support-scan`。`--preflight` 增加完整目标的 G 预检。各路分别设置模式和五行，分别接收完工和判定。[原扫描说明](../../blueprints/验收/电路/顶针逆推/support-scan.md) · [三路频道表](shared-support-scan.json) · [四路频道表](shared-support-scan-preflight.json)

| 调用路 | `enable` | `grounded` | `optional_top` | 五行（底到顶） | `done` | `accepted` |
| --- | --- | --- | --- | --- | --- | --- |
| S 筛选 | 1705200 | 1705201 | 1705202 | 1705203～07 | 1705208 | 1705209 |
| Pin 静止定位 | 1705210 | 1705211 | 1705212 | 1705213～17 | 1705218 | 1705219 |
| 递归 G | 1705220 | 1705221 | 1705222 | 1705223～27 | 1705228 | 1705229 |
| 完整目标 G 预检 | 1705240 | 1705241 | 1705242 | 1705243～47 | 1705248 | 1705249 |

1. 在 `enable=1` 前放稳 `grounded`、`optional_top` 及五行，并保持到该路释放。`grounded=0` 为 K，`1` 为 G。`optional_top=1` 允许顶层普通格未被标记。空层发空信号。
2. 选择器先送数据到扫描，留出至少 120 个信号刻并等扫描原 `done=0` 后才启动。本路 `done=1` 时采样 `accepted`。Pin 同时读取原扫描 `1704425～29` 的五行可达标记。
3. 同一路再次调用前将 `enable` 置 `0`，等本路 `done` 回到 `0` 再置 `1`。中途取消时将 `enable=0` 保持 24 个信号刻再重发。换另一路时，选择器可以在同一拍收到撤销和新请求。
4. 两路及以上请求重叠时 `1705230` 报 `fault=1`，关闭扫描并撤销回报。全部 `enable` 置 `0` 并保持 24 个信号刻，见 `fault=0` 后重新发起请求。
5. 完整目标预检使用 `grounded=1`、`optional_top=0`。收到预检 `done` 后读 `accepted`，释放预检，再由本轮主控决定是否启动 S 筛选。

## 导出和合装

```bash
python -m shapez2_tmam.circuits.compiler_backend.shared_support_scan --output shared-support-scan.spz2bp
python -m shapez2_tmam.circuits.compiler_backend.shared_support_scan --preflight --output shared-support-scan-preflight.spz2bp
```

| 蓝图 | 选择与回报平台 | 合计平台 | 建筑 |
| --- | ---: | ---: | ---: |
| 三路 | 11 | 47 | 43,016 |
| 四路 | 15 | 51 | 45,790 |

每份蓝图含一件 36 板原扫描。已有同版扫描的合装使用 `--controller-only`，由选择板独占驱动 `1704410`、`1704413`、`1704414` 和 `1704420～24`。需要改绑频道时，复制接口表并修改 `routes`，使用 `--routes 绑定.json` 导出。Pin 的可达标记仍按 `outputs.pin_reached_rows` 接线。

按每次无线传播 12 信号刻的原生接线模型，三路六次、四路八次完整调用的 `done` 均在 128,640 信号刻到达，通过位及 Pin 可达标记与 Python 一致。四路版额外核对预检到 S 的交接、预检通过和失败、六种并发组合及清故障重启。独立选择板等到旧 `done` 清零后才启动。游戏内时序待验。
