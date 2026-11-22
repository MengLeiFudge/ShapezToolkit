# 纯堆叠配方电路

目标通过本册的空隙判定和五轮扫描后，可读取每个工段的动态配方。下列蓝图把结果送到制作层提交器的私有频道。完整的动态提交仍待接入验证。

| 蓝图 | 输入 | 输出 |
|---|---|---|
| [工序和槽号](direct-recipe-fields.json) | 工段地址、配方长度 | `opcode`、`a`、`b`、`destination` |
| [基础料深度](direct-base-depth.json) | 同一工段地址和配方长度 | 从目标顶层往下数的距离，顶层为 0 |
| [读基础料](direct-base-read.json) | 原目标、基础料深度 | 对应的原生单层图形，无基础料时为空 |

对于五层以下的连续目标，配方长度为 `2h−1`。地址 0 读取底层并写槽 0。其余基础料地址 `1、3、5、7` 从第二层起依次取料并写槽 1。每次取料后的堆叠读槽 0 和槽 1，结果写回槽 0。基础料工段的两个操作数和所有工段的颜色信号留空。

保持地址、长度和原目标后，基础料经过两块板。其保持时间按两张接口表相加，当前合计 1664 信号 tick。工序和槽号与这两块板并行计算。提交器需要确认当前地址的各字段稳定。

## 重新生成

在仓库根目录运行以下命令，并把输出放进本册。

```bash
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
```
