# 正向恢复一层顶针尾部

一层逆推记录保留顶针前的制造证书、顶针后的 `pushed`，以及追加后的目标。先用证书的实际成品虚拟顶针。结果完全等于 `pushed` 后，从底到顶读取 `pushed` 和目标的对应层。只把 `pushed` 中尚未占用的普通格与针送进逐层追加。上层先按 S 前态条件保留全部晶体，并检查追加后的完整回放。

| 蓝图 | 输入 | 输出 | 保持期 |
| --- | --- | --- | ---: |
| [虚拟顶针核对](tail-frame-pin.spz2bp) | `1703703` 实际前态，`1703704` 预期顶针结果 | `1703705` 精确相等且两者有值 | 512 信号刻 |
| [当前层的追加料](tail-frame-row.spz2bp) | `1703700` 目标当前行，`1703701` 顶针结果当前行 | `1703702` 对应的无晶单层，空行输出为空 | 1664 信号刻 |
| [步骤对应的原层](tail-frame-level.spz2bp) | `1703706` 当前步骤 | `1703712` 层号，步骤 0 及结束时为 `-1` | 见同名接口表 |
| [正向六字段](tail-frame-packet.spz2bp) | `1703706` 当前步骤、`1703702` 当前追加行 | `1703707`～`1703711` 的操作号、A/B、目的槽、基础料。颜色为空 | 见同名接口表 |

每个组合方法占一块 3×3 平台。Python 离线核对了 10,000 组单层取差量结果，包含空格、针、两种普通料、晶体和所有保留掩码，另外核对了顶针通过和失配。步骤 0 对槽 0 顶针，步骤 1～10 每层先领料到槽 1，再叠回槽 0。当前追加行为空时跳过两步。多层候选保存、调度和游戏内联测仍待接续。

```bash
source=shapez2_tmam/synthesis/tail_frame.py
python -m shapez2_tmam.circuits.compile_method "$source" \
  --field accepted=tail_pin_matches --input-channel source=1703703 \
  --input-channel pushed=1703704 --output-channel accepted=1703705 --output tail-frame-pin.spz2bp
python -m shapez2_tmam.circuits.compile_method "$source" \
  --field row=tail_frame_row --input-channel target=1703700 \
  --input-channel pushed=1703701 --output-channel row=1703702 --output tail-frame-row.spz2bp
python -m shapez2_tmam.circuits.compile_method "$source" \
  --field level=tail_frame_level --input-channel step=1703706 --output-channel level=1703712 \
  --output tail-frame-level.spz2bp
python -m shapez2_tmam.circuits.compile_method "$source" \
  --field opcode=tail_frame_opcode --field a=tail_frame_a --field b=tail_frame_b \
  --field destination=tail_frame_destination --field base=tail_frame_base \
  --input-channel step=1703706 --input-channel row=1703702 --output-channel opcode=1703707 \
  --output-channel a=1703708 --output-channel b=1703709 --output-channel destination=1703710 \
  --output-channel base=1703711 --publish-when opcode=tail_frame_active \
  --publish-when a=tail_frame_uses_a --publish-when b=tail_frame_uses_b \
  --publish-when destination=tail_frame_active --publish-when base=tail_frame_uses_base \
  --output tail-frame-packet.spz2bp
```
