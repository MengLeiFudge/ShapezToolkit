# 四象限五层验收蓝图

这套蓝图用于同一条 48 工段生产线的两份订单。`stack` 是五层纯堆叠，`pin-crystal` 包含结晶和尾部顶针。实体册带固定发送器，通过频道 `1640047` 的整数 `1` 或 `2` 选单。

| 分册 | 图纸 | 接口 |
|---|---|---|
| 实体 | 48 工段、发送器与单带出口 | [完整站场及用料](实体/physical.json) |
| 实体精简版 | 同一条工道，保留两份固定订单所需的 21 个基础料站和 2 个结晶站 | [精简站场及用料](实体/six-slot-acceptance-compact.json) |
| 实体 | 固定两步订单，核对整组提交及复位 | [样件接口](实体/two-step-sender.json) |
| 实体 | 两笔六字段写入与保持接管 | [原生样件](实体/writer-handoff.spz2bp) · [接线表](实体/writer-handoff.json) |
| 实体 | 四色含晶整形，两种切向分别用 40 和 41 道工序 | [导入蓝图](实体/四色含晶/four-color.spz2bp) · [短代码、配方与站场](实体/四色含晶/four-color.json) |
| 配料 | 基础料与结晶染料的换装站、两种混合车库 | [货种、车厢、层位及接口](配料/proportioning.json) |
| 通用火车 | 图形和流体单料车的车库、装货站、卸货站 | [装载类型及方向](通用火车/trains.json) |
| 电路 | 从原图一次读取五份原色单层 | [原生蓝图](电路/原层读取/read-five-rows.spz2bp) · [接口](电路/原层读取/read-five-rows.json) |
| 电路 | 按原层号读取目标的两层 | [复位、选择与采样](电路/原层读取/read-target-rows.json) |
| 电路 | 四列逐层堆叠前缀扫描 | [整行编码](电路/堆叠前缀/pack-stack-row.json) · [复位、行输入和采样时序](电路/堆叠前缀/stack-prefix-scan.json) |
| 电路 | 筛选顶针来源及顶盖 | [单列前缀上界](电路/双半形/column-pin-prefix-limit.json) · [顶盖、接触集及通过信号](电路/顶盖筛选/cap-covers-required.json) |
| 电路 | 无晶体路线的原图稳定性和回放 | [稳定性判定](电路/纯堆叠/direct-stability.json) · [五轮扫描](电路/纯堆叠/direct-stack-scan.json) |
| 纯堆叠 | 动态制单、九工段实体、火车配料与一带出口 | [纯堆叠各分册与接线](电路/纯堆叠/README.md) |
| 电路 | 统一切向并选择当前列 | [切向转换](电路/双半形/orient-cut.json) · [四列扫描输入](电路/双半形/four-column-targets.json) · [四列调用](电路/双半形/read-four-columns.json) · [列选择](电路/双半形/select-column.json) · [前缀高度选择](电路/双半形/select-prefix-height.json) |
| 电路 | 从原图提取一列并检查列 A | [材料读取](电路/双半形/read-column.json) · [列 A 判定](电路/双半形/read-column-admissible.json) · [初始晶体高度](电路/双半形/column-crystal-height.json) |
| 电路 | 生成角的晶下落点参数和助手柱 | [前缀角参数](电路/双半形/prefix-corner-parameters.json) · [独立落点样件](电路/双半形/corner-gap.json) · [助手柱](电路/双半形/corner-helper.json) |
| 电路 | 从原图检查两列半形的支撑 | [两半顺序预处理](电路/双半形/seed-two-halves.json) · [四列合成五层材料字](电路/双半形/join-material-words.json) · [前半输入](电路/双半形/seed-pair-0.json) · [后半输入](电路/双半形/seed-pair-1.json) · [含晶区间预处理](电路/双半形/seed-crystal-half.json) · [恢复列序](电路/双半形/finish-crystal-half.json) · [五轮逐层闭包](电路/双半形/paired-prefix-scan.json) · [含晶整行编码](电路/双半形/pack-prefix-row.json) · [含晶半行编码](电路/双半形/pack-prefix-half.json) · [虚拟半切稳定性判定](电路/双半形/half-stability.json) |
| 电路 | 从原图读取已选前缀的材料和原色 | [原单格读取](电路/双半形/read-labeled-corner.json) · [前缀材料字](电路/双半形/read-prefix-column.json) · [前缀原格](电路/双半形/read-prefix-corner.json) |
| 电路 | 直接释放角的前态与外侧锚料 | [最高晶体层](电路/双半形/corner-highest-crystal.json) · [逐层原料](电路/双半形/simple-corner-source.json) |
| 电路 | 顶破角的前态与辅助锚柱 | [逐层原料](电路/双半形/pin-corner-source.json) · [近锚和远侧顶针柱](电路/双半形/pin-corner-anchors.json) |
| 电路 | 原料就位后的角级回放 | [直接释放](电路/双半形/simple-corner-release.json) · [支撑交接和顶破](电路/双半形/pin-corner-release.json) |
| 电路 | 顶破支路的补料与半形拼接 | [触顶补形](电路/双半形/pin-corner-complement.json) · [上部单层](电路/双半形/pin-corner-upper-layer.json) · [收尾](电路/双半形/pin-corner-finish.json) · [相邻两角拼接](电路/双半形/join-corner-half.json) |
| 电路 | 合并两个已制半形并追加尾部 | [整形拼接](电路/双半形/join-built-halves.json) · [上料选择](电路/双半形/tail-stack-row.json) · [逐层追加](电路/双半形/append-paired-tail.json) · [回放验收](电路/双半形/paired-order-accept.json) |
| 电路 | 带原色的紧柱备料与回放 | [单步备料](电路/双半形/dense-column-actions.json) · [五轮回放](电路/双半形/dense-column.json) · [完工取柱](电路/双半形/dense-column-finish.json) |

单料车把同一种货物送往配料站。配料站按装载表把每种货物放入混合车的指定层，再由混合车向制作工段供货。同一车厢每层的带或管使用同一种物料。游戏内按坐标接轨、装方、开料和换单，验收时记录满带出货和卸货量。实机持续产量待测。

生成命令、运行顺序和测量格式见[六槽实体装配](../../circuits/factory_assembly/README.md)。整厂接口见[蓝图约定](../整厂约定.md)。

五层原色读取板接已经统一切向的目标 `1700872`。经过 1920 信号 tick 后，从 `1701200` 到 `1701204` 依次读第一层到第五层。空层输出空信号，其他层保留原有材料和颜色。一块 3×3 平台使用三层电路空间，内部通过本地接线。

可选两层的读取电路将目标接 `initial_remaining`，`initial_top`、`initial_below` 留空。`item0` 至 `item4` 对应原第五层到第一层。填写 `1` 的层位写入 `result_top`，填写 `2` 的层位写入 `result_below`，其余填写 `0`。到采样时刻且 `done=1` 后读结果，所选层原本为空时输出空信号。

整行编码板从当前层与正下方一层读取堆叠支撑，`ground=1` 对应第一层。两块平台间用五对飞线。含晶编码用针标出已经保留的晶体，供双半形闭包使用。半行板只保留 q0/q1。整行板两块相邻平台通过七对原生飞线传递内部数据。

前缀扫描电路接受四列初始前缀高度和五份已编码的行。每轮从同一份旧高度计算四列，依次处理第五层到第一层。电路与实体订单分别验收，实体册当前由固定发送器供给配方。

纯堆叠电路的目标输入为 `1600000`。稳定性判定板同时转发目标和初始通过位。`initial_replay` 留空。按接口表启动五轮扫描，待 `done=1` 后再采样。装方信息板将实际回放与目标比较，通过后才发布配方长度和回放结果。

列读取每次处理 `q0`。将待查列旋转到 `q0`，原图接 `initial_remaining`，`initial_word` 留空，`initial_height` 置 5。五轮后输出保留全部原层位的材料图形，其中 `Cu`、`Ru`、`Su`、`Wu` 依次表示空、普通格、针和晶体。判定与落点两块板共用材料频道。等读取器到采样时刻且 `done=1` 后，再按各接口表等满保持时间。`column_a=1` 时，`crystal` 和 `landing` 给出晶下间隙的原层号，从 0 起算。无间隙时两者为 `-1`。`needs_pin=1` 表示该落点须走顶破路线。换列前重新复位。

前半输入板读 q0/q1 材料字，后半输入板读 q2/q3 材料字。它们各自扫描最高晶体，给出按高度排列的两份材料字、两个高度和交换标志。等这组数据稳定后启动含晶区间预处理。四列完工会启动两半预处理调用器。首轮等待 2184 tick，包含参数稳定和被调用板复位。第二轮只等普通复位。两个结果经前、后半的恢复列序板直接送到五轮闭包的四个初值口。 [前半恢复](电路/双半形/restore-seed-0.json) · [后半恢复](电路/双半形/restore-seed-1.json)独立调试可直接向排序板提供已有的高度。 [独立排序接口](电路/双半形/order-crystal-half.json)较低列高度置入 `initial_required`，较高列高度置入 `high_height`。无晶体列的高度为 `0`。`initial_candidate` 和 `initial_supported` 都置 `0`。五轮后只读取 `result_required`。该值是较低列的新前缀高度，`-1` 表示含晶区间无法由这个半边支撑。恢复列序板沿用较高列的输入高度，按原左右列输出两份前缀高度。普通层的支撑由逐层闭包继续判定。

切向转换板用 `alternate` 将两个切向统一到 q0/q1 和 q2/q3。四列输入板同时输出四种旋转，每种都把对应列转到 q0。调用器按 q0 到 q3 的顺序复用一套列读取模块，四次均读全高。批次 `done=1` 后从 `1700963–1700966` 读四份材料字。 [四次调用参数](电路/双半形/read-four-columns-calls.json)`select-column` 将 `column` 指定的一列转到 q0，把同一图形送给全列和前缀材料读取器。前缀高度选择板也使用这个列号。五轮闭包完成前，或任一列返回 `-1` 时，高度选择板给出 `-1`，不开始该列的实体配方。四列初值接两块半形预处理的结果，`item0` 至 `item4` 接从最高到最低的五份含晶支撑行。前缀结果出现 `-1` 时，该切向不能直接用双半形和堆叠制作。其他结果可送往前缀材料读取板。完成换向后，制造端将输出旋转回目标方位。

读取整列可将 `read-prefix-column` 的 `prefix_height` 保持为 `5`。已选定前缀高度后，将同一高度送给 `read-prefix-column` 和 `read-prefix-corner`。材料字仍保留五个原层位，超出前缀的格记为空。把材料字接到落点判定，把原格接到备料板。原格输出保留普通图形和晶体的颜色。前缀高度为 `0` 时该列为空。

半形支撑检查的图形只占 `q0/q1`。把它接入 `target`，等满接口表的保持时间后读 `result`。虚拟半切后图形与输入相等时输出 `1`。含晶体半形还要对每列分别检查列 A。

直接释放的原料板接收正在处理的原格、落点层的原格及其层号。列 A 通过且 `needs_pin=0` 时，`main` 给出该层的主列前态，`far` 给出外侧锚柱该层材料。原色由单格读取模块保留。

顶破路线的原料板读取原目标的上一层格、落点原格、地面原格与当前层号，输出截去顶层前的主列格及初次底部补晶使用的远柱格。近锚和远侧顶针柱由同一组落点参数生成，输出统一在 q0。触顶补形板接远侧顶针柱，和 q2 的触顶晶体柱合并。角级回放板接受已组装的前态、近锚和补形，依次执行底部碎晶、支撑交接和顶破。

收尾板接顶破结果与依原层号排列的五份上部单层，未使用的层位留空。释放、补形、上部单层和收尾共用频道 `1700678`。发 `0` 时助手在 q1，发 `1` 时助手在 q3。角参数合装板接前缀材料字，向已有备料口同时发布最高晶层、间隙、落点和顶破选择。合装时用它替换独立的落点板和最高晶层板。

列选择板同时发布助手方向。角结果板按顶破选择取一份已完成角，前缀为空时输出空信号。半形拼接板接收按次保存的两角，主列分别在 q0、q1，助手分别在 q3、q2。 [角结果选择](电路/双半形/place-released-corner.json)

整形拼接接收两个均占 q0/q1 的已制半形，空侧留空。`alternate=1` 将结果顺时针转一象限以恢复另一切向的原方位。上料选择板读目标的一个原单层、从 0 起算的层号和四列的闭合前缀高度。它保留各列前缀以外的普通格和针。尾部板接拼接结果和按原层号排列的五份已选上料，空层留空。回放验收板比较追加后的整形和原目标，同时要求主控给出有效和完工信号。逐层调用与实体工序由主控调度。

紧柱回放的 `item0` 至 `item4` 顺序为从底到顶，每次送入已在 q0 上的普通格或有色晶体。目标柱连续，空信号只用于末尾补齐。`initial_source` 和 `initial_pending` 留空。等五轮完成后再按完工板接口表读取结果。回放实现了同色晶体批量结晶，实际下料与工序提交由制作层处理。

```bash
python -m shapez2_tmam.circuits.compile_method shapez2_tmam/synthesis/shape_methods.py \
  --field row0=original_row_0 --field row1=original_row_1 --field row2=original_row_2 \
  --field row3=original_row_3 --field row4=original_row_4 --input-channel target=1700872 \
  --output-channel row0=1701200 --output-channel row1=1701201 --output-channel row2=1701202 \
  --output-channel row3=1701203 --output-channel row4=1701204 --output read-five-rows.spz2bp
python -m shapez2_tmam.circuits.compile_stack_scan --read-rows --channel-base 1700300 --output read-target-rows.spz2bp
python -m shapez2_tmam.circuits.compile_stack_scan --channel-base 1700200 --output stack-prefix-scan.spz2bp
python -m shapez2_tmam.circuits.compile_stack_scan --check-direct --channel-base 1700450 --output direct-stack-scan.spz2bp
python -m shapez2_tmam.circuits.compile_method shapez2_tmam/synthesis/half_support.py \
  half_is_stable --channel-base 1700600 --output half-stability.spz2bp
python -m shapez2_tmam.circuits.compile_stack_scan --read-column --channel-base 1700560 --output read-column.spz2bp
python -m shapez2_tmam.circuits.compile_method shapez2_tmam/synthesis/column_scan.py \
  --field crystal=column_gap_crystal --field landing=column_gap_landing \
  --field needs_pin=column_gap_needs_pin --input-channel word=1700566 \
  --output-channel crystal=1700577 --output-channel landing=1700578 \
  --output-channel needs_pin=1700579 --output corner-gap.spz2bp
python -m shapez2_tmam.circuits.compile_method shapez2_tmam/synthesis/column_scan.py \
  --field helper=corner_helper_column --input-channel crystal=1700577 \
  --input-channel landing=1700578 --input-channel suspended=1700579 \
  --output-channel helper=1700587 --output corner-helper.spz2bp
python -m shapez2_tmam.circuits.compile_method shapez2_tmam/synthesis/shape_methods.py \
  read_labeled_corner --channel-base 1700620 --output read-labeled-corner.spz2bp
python -m shapez2_tmam.circuits.compile_stack_scan --read-prefix-column --channel-base 1700800 --output read-prefix-column.spz2bp
python -m shapez2_tmam.circuits.compile_method shapez2_tmam/synthesis/shape_methods.py \
  read_prefix_corner --channel-base 1700790 --output read-prefix-corner.spz2bp
python -m shapez2_tmam.circuits.compile_method shapez2_tmam/synthesis/shape_methods.py \
  pack_stack_row --channel-base 1700740 --output pack-stack-row.spz2bp
python -m shapez2_tmam.circuits.compile_method shapez2_tmam/synthesis/shape_methods.py \
  pack_prefix_half --channel-base 1700820 --output pack-prefix-half.spz2bp
python -m shapez2_tmam.circuits.compile_stack_scan --seed-crystal-half --channel-base 1700830 --output seed-crystal-half.spz2bp
python -m shapez2_tmam.circuits.compile_method shapez2_tmam/synthesis/crystal_support.py \
  --field low_word=seed_low_word --field high_word=seed_high_word --field initial_required=seed_low_height \
  --field high_height=seed_high_height --field swapped=seed_swap --input-channel left_word=1700850 \
  --input-channel right_word=1700851 --input-channel left_height=1700852 --input-channel right_height=1700853 \
  --output-channel low_word=1700846 --output-channel high_word=1700847 --output-channel initial_required=1700831 \
  --output-channel high_height=1700848 --output-channel swapped=1700854 --output order-crystal-half.spz2bp
python -m shapez2_tmam.circuits.compile_method shapez2_tmam/synthesis/crystal_support.py \
  --field left=seed_left --field right=seed_right --input-channel required=1700835 \
  --input-channel high_height=1700848 --input-channel swapped=1700854 \
  --output-channel left=1700855 --output-channel right=1700856 --output finish-crystal-half.spz2bp
python -m shapez2_tmam.circuits.compile_stack_scan --close-prefix --channel-base 1700760 --output paired-prefix-scan.spz2bp
python -m shapez2_tmam.circuits.compile_method shapez2_tmam/synthesis/column_scan.py \
  --field height=column_crystal_height --input-channel word=1700566 \
  --output-channel height=1700858 --output column-crystal-height.spz2bp
python -m shapez2_tmam.circuits.compile_method shapez2_tmam/synthesis/prefix_route.py \
  --field target=orient_cut --input-channel target=1600000 --input-channel alternate=1700871 \
  --output-channel target=1700872 --output orient-cut.spz2bp
python -m shapez2_tmam.circuits.compile_method shapez2_tmam/synthesis/prefix_route.py \
  --field original=select_column --field prefix=select_column --field counterclockwise=select_column_handedness \
  --input-channel target=1700872 --input-channel column=1700873 --output-channel original=1700561 \
  --output-channel prefix=1700801 --output-channel counterclockwise=1700678 --output select-column.spz2bp
python -m shapez2_tmam.circuits.compile_method shapez2_tmam/synthesis/prefix_route.py \
  --field height=select_prefix_height --input-channel done=1700765 --input-channel h0=1700766 \
  --input-channel h1=1700767 --input-channel h2=1700768 --input-channel h3=1700769 \
  --input-channel column=1700873 --output-channel height=1700816 --output select-prefix-height.spz2bp
python -m shapez2_tmam.circuits.compile_method shapez2_tmam/synthesis/shape_methods.py \
  --field support=pack_prefix_row --input-channel row=1700306 --input-channel below=1700307 \
  --input-channel ground=1700880 --output-channel support=1700881 --output pack-prefix-row.spz2bp
python -m shapez2_tmam.circuits.compile_method shapez2_tmam/synthesis/column_scan.py \
  --field limit=column_pin_prefix_limit --input-channel word=1700566 \
  --output-channel limit=1700887 --output column-pin-prefix-limit.spz2bp
python -m shapez2_tmam.circuits.compile_method shapez2_tmam/synthesis/column_scan.py \
  --field crystal=column_gap_crystal --field landing=column_gap_landing --field needs_pin=column_gap_needs_pin \
  --field highest=column_highest_crystal --input-channel word=1700806 --output-channel crystal=1700577 \
  --output-channel landing=1700578 --output-channel needs_pin=1700579 --output-channel highest=1700588 \
  --output prefix-corner-parameters.spz2bp
python -m shapez2_tmam.circuits.compile_method shapez2_tmam/synthesis/prefix_route.py \
  --field corner=place_released_corner --input-channel simple=1700672 --input-channel broken=1700695 \
  --input-channel needs_pin=1700579 --input-channel column=1700873 --input-channel prefix_height=1700816 \
  --output-channel corner=1700890 --output place-released-corner.spz2bp
python -m shapez2_tmam.circuits.compile_method shapez2_tmam/synthesis/direct_stack.py \
  --field accepted=direct_order_accepted --input-channel target=1600000 --input-channel replay=1700719 \
  --input-channel valid=1700894 --input-channel done=1700895 --output-channel accepted=1700896 \
  --output paired-order-accept.spz2bp
python -m shapez2_tmam.circuits.compile_method shapez2_tmam/synthesis/prefix_route.py \
  --field q0=column_target_q0 --field q1=column_target_q1 --field q2=column_target_q2 --field q3=column_target_q3 \
  --input-channel target=1700872 --output-channel q0=1700898 --output-channel q1=1700899 \
  --output-channel q2=1700900 --output-channel q3=1700901 --output four-column-targets.spz2bp
python -m shapez2_tmam.circuits.compiler_backend.module_caller \
  shapez2_tmam/blueprints/验收/电路/双半形/read-prefix-column.json \
  shapez2_tmam/blueprints/验收/电路/双半形/read-four-columns-calls.json \
  --channel-base 1700930 --result result_word \
  --callee shapez2_tmam/blueprints/验收/电路/双半形/read-prefix-column.spz2bp --output read-four-columns.spz2bp
for pair in 0 1; do
  first=$((1700963 + 2 * pair))
  out=$((1701040 + 5 * pair))
  python -m shapez2_tmam.circuits.compile_method shapez2_tmam/synthesis/crystal_support.py \
    --field low_word=pair_seed_low_word --field high_word=pair_seed_high_word \
    --field low_height=pair_seed_low_height --field high_height=pair_seed_high_height --field swapped=pair_seed_swap \
    --input-channel left_word="$first" --input-channel right_word="$((first + 1))" \
    --output-channel low_word="$out" --output-channel high_word="$((out + 1))" \
    --output-channel low_height="$((out + 2))" --output-channel high_height="$((out + 3))" \
    --output-channel swapped="$((out + 4))" --output "seed-pair-$pair.spz2bp"
done
python -m shapez2_tmam.circuits.compiler_backend.module_caller \
  shapez2_tmam/blueprints/验收/电路/双半形/seed-crystal-half.json \
  shapez2_tmam/blueprints/验收/电路/双半形/seed-two-halves-calls.json \
  --channel-base 1701070 --result result_required --enable-channel 1700932 --parameter-hold-signal-ticks 1920 \
  --callee shapez2_tmam/blueprints/验收/电路/双半形/seed-crystal-half.spz2bp --output seed-two-halves.spz2bp
for pair in 0 1; do
  high=$((1701043 + 5 * pair))
  output=$((1700761 + 2 * pair))
  python -m shapez2_tmam.circuits.compile_method shapez2_tmam/synthesis/crystal_support.py \
    --field left=seed_left --field right=seed_right --input-channel required="$((1701099 + pair))" \
    --input-channel high_height="$high" --input-channel swapped="$((high + 1))" \
    --output-channel left="$output" --output-channel right="$((output + 1))" --output "restore-seed-$pair.spz2bp"
done
python -m shapez2_tmam.circuits.compile_method shapez2_tmam/synthesis/material_word.py \
  --field word=join_material_words --input-channel q0=1700963 --input-channel q1=1700964 \
  --input-channel q2=1700965 --input-channel q3=1700966 --output-channel word=1701120 \
  --output join-material-words.spz2bp
python -m shapez2_tmam.circuits.factory_assembly.acceptance --four-color --compact --output four-color.spz2bp
```
