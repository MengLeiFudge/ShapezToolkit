# 单次顶针层的候选调用

`pin-layer-search.spz2bp` 依次控制四列枚举、五层封存、双来源闭包、制造证书请求和顶针回放请求。每次只处理已经选定的 `pushed` 目标的一层顶针逆推。上层负责遍历堆叠前态、提供制造证书以及继续处理递归尾部。

策略入口 `attempts(target, slots, lowest, remaining_pins)` 接收 `pushed` 图形、当前四个冻结槽号、上一层搜索的最低晶层和本层之后可用的顶针次数。它用 `pin_families` 校验最大族的顶针像与接触掩码，按下降顺序给出合法掩码。每族先给模板。只有模板闭包耗尽后才继续读生成器。允许继续递归的族接着按 `PinFamily.members()` 的顺序给出成员。成员沿用 `skip_start=True` 的规则，直接请求证书。策略提供方可以用 Python 入口生成本次调用的参数。

| 信号 | 频道 | 约定 |
| --- | ---: | --- |
| `enable` | 1703300 | 启动前置 0 至少 456 信号刻，再置 1 |
| `plan_ready`、`kind`、`mask` | 1703301～1703303 | 本次参数稳定后置 `plan_ready=1`。`kind=1` 为模板，`2` 为成员，`0` 表示当前四槽已查完 |
| `members` | 1703308～1703311 | q0～q3，`0` 空格、`1` 普通块、`2` 针。晶体掩码覆盖的列使用掩码 |
| `plan` | 1703312 | 置 1 时，从冻结的四列槽号取得下一次参数。保持参数和 `plan_ready` 到请求降为 0 |
| `reject` | 1703313 | `1` 表示模板两种切向都耗尽，`2` 表示这一成员的递归搜索已耗尽。处理回报后将 `plan_ready` 拉低 |
| `proof` | 1703314 | 请求当前制造证书。模板已成功闭包，成员按递归入口请求 |
| `proof_done`、`proof_ok` | 1703304、1703305 | `done=1` 时回报结果。`ok=1` 交付完整证书，`ok=0` 表示已穷尽 |
| `replay` | 1703315 | 用证书实际产出的槽 0 形状做一次顶针，并与 `pushed` 比较 |
| `replay_done`、`replay_ok` | 1703306、1703307 | `done=1` 且 `ok=1` 表示本次回放和目标匹配 |
| `accepted`、`exhausted`、`fault` | 1703316～1703318 | 分别表示已验收、四列枚举已穷尽、当前协议或验收失败。结果保持到复位 |

每次新尝试先复位封存和闭包，并确认封存、闭包、证书和回放的旧回报均已拉低。四槽的全部族和所需成员查完后，策略端回 `kind=0`。控制器等四列 `ready` 拉低才结束 `advance`。只有四列枚举报告耗尽才发布 `exhausted`。模板已获闭包却未能生成证书、缺少明确证书回报、顶针回放失配或尝试中途失去冻结候选，均进入 `fault`。

四列输入使用 `pin-column-sample.json` 的材料字频道。原目标五行仍由 `1701200`～`1701204` 输入读取器。控制蓝图与四列枚举、五层读取、五层封存及双来源闭包合装。证书生成和回放接口由上层连接，回放使用证书实际产出的前态。可选顶盖模板中的辅助普通格只有在制造证书需要时才会出现在实际前态。

```powershell
py -B -X utf8 -m shapez2_tmam.circuits.compiler_frontend.pin_layer_search `
  shapez2_tmam/blueprints/验收/电路/顶针逆推/pin-column-sample.json `
  shapez2_tmam/blueprints/验收/电路/顶针逆推/pin-source-rows.json `
  shapez2_tmam/blueprints/验收/电路/顶针逆推/dual-source-closure.json `
  --output pin-layer-search.spz2bp
```

离线回放按板内同拍和无线 12 信号刻计算。223 板原生合装对 `P-P-P-P-:CuRuSuWu:CuRuSuWu:CuRuSuWu:CuRuSuWu` 取得槽号 `(0, 0, 0, 0)` 与掩码 `15`，实际跑完封存及闭包。Python 生成制造证书并做正向顶针比较，两项回报都到达后，控制器才接受。另一真实族按掩码 `8` 排出 1 个模板和 18 个成员。控制蓝图用模拟回报单独覆盖了模板失败、成员续查、旧回放回报、四列耗尽和回放失配。游戏内联动待验收。
