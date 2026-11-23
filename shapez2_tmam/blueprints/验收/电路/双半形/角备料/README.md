# 角备料与释放

四个角共用原色取料和释放电路。先保留选定切向，再提供当前列号 `1700873`。所选前缀的高度从 `1700816` 读取。前缀角参数板提供最高晶层 `1700588`、晶下间隙 `1700577`、落点 `1700578` 和顶破选择 `1700579`。

| 电路 | 输入与结果 |
| --- | --- |
| [当前层](read-corner-work-label.json) | `1701615` 选工作层。直接释放读该层，顶破读其上一原层。结果 `1701612`。 |
| [落点层](read-corner-gap-label.json) | 根据落点层号读 `1701613`。无落点时为空。 |
| [底层](read-corner-ground-label.json) | 读前缀地面原格 `1701614`。原格为针时保留针信号。 |
| [本层前态材料](prepare-corner-layer.json) | 读三份原格和前缀角参数，发布主列 `1701616` 与远锚 `1701617`。 |

三个读取电路共用五份原色行 `1701200` 至 `1701204`，所有单格输出均放在 q0。工作层从零起算。列号或层号变化后，先按读取器接口等满三个读取器的最长保持时间，再按本层前态材料的接口等待后级稳定。前态材料须由主控送到备料方法。主列含晶前缀、针前缀和普通后缀各自按对应工序制作。直接释放没有临时填晶时无需造远锚。

顶破前态的目标底格为空或为针时，主列的临时填晶与远锚同层接触。目标底格为针时，底部针在顶破时重新生成。[顶破逐层原料](../pin-corner-source.json)

## 释放指令

| 信号 | 频道 | 含义 |
| --- | --- | --- |
| `stage` | 1701660 | `0` 直接释放，共 5 个步位。`1` 支撑交接，共 18 个步位。`2` 最后顶破，共 4 个步位。 |
| `step` | 1701661 | 从 `0` 起算。指令为空时可跳过该步位。交接完毕后先制作补形，再进入阶段 `2`。 |
| `counterclockwise` | 1700678 | `0` 表示助手在 q1，`1` 表示助手在 q3。 |
| `main` | 1701662 | 当前主形槽。 |
| `support` | 1701663 | 阶段 `0` 为远锚，`1` 为近锚，`2` 为补形。直接释放无需远锚时提供 `-1`。 |
| `far`、`upper` | 1701664、1701665 | 阶段 `1` 的两份临时空槽，用于逐层堆成五层远柱。 |
| 六字段 | 1701666 至 1701670 | 依次为操作号、a、b、目的槽、基础料。染料频道留空。 |

[支撑交接](corner-handoff-word.json)负责各步的远柱与交接顺序，[释放步位](corner-release-word.json)选择本阶段的操作，[释放配方](corner-release-packet.json)把操作展开为制作层字段。导入三块板，按三份接口表的总保持时间采样。确认操作号为有效信号后再读取整组，槽号 `0` 有效。主控负责等同址写入确认后再推进到下一步位。

## 重导

```bash
for spec in 'work original 1701612' 'gap moved 1701613' 'ground ground 1701614'; do
  read -r mode field output <<< "$spec"
  args=(--input-channel row0=1701200 --input-channel column=1700873 --input-channel height=1700816)
  if [[ "$mode" != ground ]]; then
    args+=(--input-channel row1=1701201 --input-channel row2=1701202)
  fi
  if [[ "$mode" == work ]]; then
    args+=(--input-channel row3=1701203 --input-channel row4=1701204 --input-channel level=1701615 --input-channel needs_pin=1700579)
  elif [[ "$mode" == gap ]]; then
    args+=(--input-channel landing=1700578)
  fi
  python -m shapez2_tmam.circuits.compile_method shapez2_tmam/synthesis/corner_inputs.py \
    --field "$field=corner_${mode}_label" "${args[@]}" --output-channel "$field=$output" --output "read-corner-$mode-label.spz2bp"
done
python -m shapez2_tmam.circuits.compile_method shapez2_tmam/synthesis/corner_inputs.py \
  --field main=corner_main_input --field far=corner_far_input --input-channel original=1701612 \
  --input-channel moved=1701613 --input-channel ground=1701614 --input-channel level=1701615 \
  --input-channel height=1700816 --input-channel highest=1700588 --input-channel crystal=1700577 \
  --input-channel landing=1700578 --input-channel needs_pin=1700579 --output-channel main=1701616 \
  --output-channel far=1701617 --output prepare-corner-layer.spz2bp
python -m shapez2_tmam.circuits.compile_method shapez2_tmam/synthesis/release_packet.py \
  --field word=release_handoff_word --input-channel step=1701661 --input-channel counterclockwise=1700678 \
  --output-channel word=1701672 --output corner-handoff-word.spz2bp
python -m shapez2_tmam.circuits.compile_method shapez2_tmam/synthesis/release_packet.py \
  --field word=release_word --input-channel stage=1701660 --input-channel step=1701661 \
  --input-channel counterclockwise=1700678 --input-channel support=1701663 --input-channel handoff_word=1701672 \
  --output-channel word=1701671 --output corner-release-word.spz2bp
python -m shapez2_tmam.circuits.compile_method shapez2_tmam/synthesis/release_packet.py \
  --field opcode=release_opcode --field a=release_a --field b=release_b \
  --field destination=release_destination --field base=release_base \
  --publish-when opcode=release_has_packet --publish-when a=release_uses_a --publish-when b=release_uses_b \
  --publish-when destination=release_has_packet --publish-when base=release_uses_base \
  --input-channel word=1701671 --input-channel counterclockwise=1700678 --input-channel main=1701662 \
  --input-channel support=1701663 --input-channel far=1701664 --input-channel upper=1701665 \
  --output-channel opcode=1701666 --output-channel a=1701667 --output-channel b=1701668 \
  --output-channel destination=1701669 --output-channel base=1701670 --output corner-release-packet.spz2bp
```
