# 纯堆叠配方电路

目标通过本册的空隙判定和五轮扫描后，电路按工段地址输出动态配方。提交桥向六槽工道提交配方。已离线核对蓝图频道及两层订单，游戏内锁存与持续出货仍待验收。

| 蓝图 | 输入 | 输出 |
|---|---|---|
| [空隙判定](direct-no-gaps.json) | 原目标 | 原目标、初始通过位 |
| [五轮扫描](direct-stack-scan.json) | 初始值和运行位 | 完成位、相邻层检查结果、实际回放 |
| [装方信息](direct-order-header.json) | 原目标及扫描结果 | 通过位、配方长度、回放图形 |
| [工序和槽号](direct-recipe-fields.json) | 工段地址、配方长度 | `opcode`、`a`、`b`、`destination` |
| [基础料深度](direct-base-depth.json) | 同一工段地址和配方长度 | 从目标顶层往下数的距离，顶层为 0 |
| [读基础料](direct-base-read.json) | 原目标、基础料深度 | 对应的原生单层图形，无基础料时为空 |
| [动态提交桥](direct-submit-bridge.json) | 工道地址、换单状态、通过位和候选六字段 | 工道六字段与确认标签 |

对于不超过五层的连续目标，配方长度为 `2h−1`。地址 0 读取底层并写槽 0。其余基础料地址 `1、3、5、7` 从第二层起依次取料并写槽 1。每次取料后的堆叠读槽 0 和槽 1，结果写回槽 0。基础料工段的两个操作数和所有工段的颜色信号留空。

保持地址、长度和原目标后，基础料经过两块板。按两张接口表合计须等待 1664 信号 tick。工序和槽号与基础料并行计算。提交桥以 12 tick 为节拍复用计数器，实际等待 1668 tick。工道地址变动或资格中断会重计。游戏内使用外置主控版实体线，并保持 `1600000` 的目标直到该单排空。

## 重新生成

在仓库根目录运行以下命令，并把输出放进本册。

```bash
python -m shapez2_tmam.circuits.compile_method shapez2_tmam/synthesis/direct_stack.py \
  --field target=direct_scan_target --field valid=has_contiguous_rows \
  --input-channel target=1600000 --output-channel target=1700451 \
  --output-channel valid=1700453 --output direct-no-gaps.spz2bp

python -m shapez2_tmam.circuits.compile_stack_scan \
  --check-direct --channel-base 1700450 --output direct-stack-scan.spz2bp

python -m shapez2_tmam.circuits.compile_method shapez2_tmam/synthesis/direct_stack.py \
  --field accepted=direct_order_accepted --field length=direct_order_length \
  --field replay=direct_order_replay --input-channel target=1600000 \
  --input-channel replay=1700459 --input-channel valid=1700458 --input-channel done=1700455 \
  --output-channel accepted=1640045 --output-channel length=1640043 \
  --output-channel replay=1640044 --publish-when length=direct_order_accepted \
  --publish-when replay=direct_order_accepted --output direct-order-header.spz2bp

python -m shapez2_tmam.circuits.compile_method shapez2_tmam/synthesis/direct_recipe.py \
  --field opcode=direct_recipe_opcode --field a=direct_recipe_lower \
  --field b=direct_recipe_upper --field destination=direct_recipe_destination \
  --input-channel address=1640000 --input-channel length=1640043 \
  --output-channel opcode=1680001 --output-channel a=1680002 \
  --output-channel b=1680003 --output-channel destination=1680004 \
  --publish-when opcode=direct_recipe_has_step --publish-when a=direct_recipe_uses_operands \
  --publish-when b=direct_recipe_uses_operands --publish-when destination=direct_recipe_has_step \
  --output direct-recipe-fields.spz2bp

python -m shapez2_tmam.circuits.compile_method shapez2_tmam/synthesis/direct_recipe.py \
  --field depth=direct_recipe_base_depth --input-channel address=1640000 \
  --input-channel length=1640043 --output-channel depth=1700580 \
  --output direct-base-depth.spz2bp

python -m shapez2_tmam.circuits.compile_method shapez2_tmam/synthesis/direct_stack.py \
  --field base=direct_base_at_depth --input-channel target=1600000 \
  --input-channel depth=1700580 --output-channel base=1680005 \
  --output direct-base-read.spz2bp

python -m shapez2_tmam.circuits.factory_assembly.submit_bridge \
  --direct-stack --hold-signal-ticks 1664 --output direct-submit-bridge.spz2bp
```
