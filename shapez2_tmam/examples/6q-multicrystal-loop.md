# 六象限完整目标：多晶体列共用脚手架

把H内侧的普通格改为晶体，两个不同晶体组仍互相支撑。脚手架逐列接管支撑，反向反复调用同一角程序；两份半形最后拼接，不追加重力。

配置：6象限、5层上限。

目标（从底到顶，q0为每层最左格）：

`Cu----Cu----:------------:crCuCucrCuCu:cr--crcr--cr:crCuCucrCuCu`

共231步，含基础供料；不是最短路径。输入编号指向已完成物品，使用后消耗。
物品槽峰值为5，不含搜索状态及传输缓存；[槽数调度证明](../general/recipe-slots.md)。
同一子配方出现两次时分别生产。Cut/Swap的另一个出口弃置；按表中出口继续。

[操作与方向说明](README.md)；本配方未在游戏中验证。

## 关键阶段

以下按原构造的标准朝向示意；实际方向及物品编号以完整步骤表为准。

| 阶段 | 结果 |
|---|---|
| 两个晶体组互相支撑的半形 | `Cu----------:------------:crCuCu------:cr--cr------:crCuCu------` |
| 双半形拼接成品 | `Cu----Cu----:------------:crCuCucrCuCu:cr--crcr--cr:crCuCucrCuCu` |

## 完整步骤

| 编号 | 加工 | 输入编号 | 参数 | 产物 |
|---:|---|---|---|---|
| 0 | base | — | — | `--------Cu--` |
| 1 | base | — | — | `--------Cu--` |
| 2 | stack | 0, 1 | — | `--------Cu--:--------Cu--` |
| 3 | base | — | — | `--------CuCu` |
| 4 | stack | 2, 3 | — | `--------Cu--:--------Cu--:--------CuCu` |
| 5 | base | — | — | `--------Cu--` |
| 6 | stack | 4, 5 | — | `--------Cu--:--------Cu--:--------CuCu:--------Cu--` |
| 7 | base | — | — | `--------CuCu` |
| 8 | stack | 6, 7 | — | `--------Cu--:--------Cu--:--------CuCu:--------Cu--:--------CuCu` |
| 9 | base | — | — | `CuCu--------` |
| 10 | base | — | — | `CuCu--------` |
| 11 | stack | 9, 10 | — | `CuCu--------:CuCu--------` |
| 12 | base | — | — | `CuCu--------` |
| 13 | stack | 11, 12 | — | `CuCu--------:CuCu--------:CuCu--------` |
| 14 | base | — | — | `CuCu--------` |
| 15 | stack | 13, 14 | — | `CuCu--------:CuCu--------:CuCu--------:CuCu--------` |
| 16 | base | — | — | `CuCu--------` |
| 17 | stack | 15, 16 | — | `CuCu--------:CuCu--------:CuCu--------:CuCu--------:CuCu--------` |
| 18 | swap | 8, 17 | 1 | `CuCu----Cu--:CuCu----Cu--:CuCu----CuCu:CuCu----Cu--:CuCu----CuCu` |
| 19 | rotate | 18 | 5 | `Cu----Cu--Cu:Cu----Cu--Cu:Cu----CuCuCu:Cu----Cu--Cu:Cu----CuCuCu` |
| 20 | cut | 19 | 1 | `------Cu--Cu:------Cu--Cu:------CuCuCu:------Cu--Cu:------CuCuCu` |
| 21 | rotate | 20 | 1 | `Cu------Cu--:Cu------Cu--:Cu------CuCu:Cu------Cu--:Cu------CuCu` |
| 22 | cut | 21 | 1 | `--------Cu--:--------Cu--:--------CuCu:--------Cu--:--------CuCu` |
| 23 | base | — | — | `CuCuCuCuCuP-` |
| 24 | base | — | — | `CuCuCuCuCuP-` |
| 25 | stack | 23, 24 | — | `CuCuCuCuCuP-:CuCuCuCuCuP-` |
| 26 | base | — | — | `CuCuCuCuCuCu` |
| 27 | stack | 25, 26 | — | `CuCuCuCuCuP-:CuCuCuCuCuP-:CuCuCuCuCuCu` |
| 28 | base | — | — | `CuCuCuCuCuP-` |
| 29 | stack | 27, 28 | — | `CuCuCuCuCuP-:CuCuCuCuCuP-:CuCuCuCuCuCu:CuCuCuCuCuP-` |
| 30 | crystal | 29 | r | `CuCuCuCuCucr:CuCuCuCuCucr:CuCuCuCuCuCu:CuCuCuCuCucr` |
| 31 | cut | 30 | 1 | `------CuCucr:------CuCucr:------CuCuCu:------CuCucr` |
| 32 | rotate | 31 | 5 | `----CuCucr--:----CuCucr--:----CuCuCu--:----CuCucr--` |
| 33 | cut | 32 | 1 | `------Cucr--:------Cucr--:------CuCu--:------Cucr--` |
| 34 | rotate | 33 | 1 | `--------Cucr:--------Cucr:--------CuCu:--------Cucr` |
| 35 | base | — | — | `--------CuCu` |
| 36 | stack | 34, 35 | — | `--------Cucr:--------Cucr:--------CuCu:--------Cucr:--------CuCu` |
| 37 | base | — | — | `CuCuCuCuCuCu` |
| 38 | base | — | — | `CuP-P-CuCuCu` |
| 39 | stack | 37, 38 | — | `CuCuCuCuCuCu:CuP-P-CuCuCu` |
| 40 | crystal | 39 | r | `CuCuCuCuCuCu:CucrcrCuCuCu` |
| 41 | cut | 40 | 0 | `CuCuCu------:Cucrcr------` |
| 42 | rotate | 41 | 5 | `CuCu------Cu:crcr------Cu` |
| 43 | cut | 42 | 0 | `CuCu--------:crcr--------` |
| 44 | base | — | — | `CuCu--------` |
| 45 | stack | 43, 44 | — | `CuCu--------:crcr--------:CuCu--------` |
| 46 | base | — | — | `CuCu--------` |
| 47 | stack | 45, 46 | — | `CuCu--------:crcr--------:CuCu--------:CuCu--------` |
| 48 | base | — | — | `CuCu--------` |
| 49 | stack | 47, 48 | — | `CuCu--------:crcr--------:CuCu--------:CuCu--------:CuCu--------` |
| 50 | swap | 36, 49 | 1 | `CuCu----Cucr:crcr----Cucr:CuCu----CuCu:CuCu----Cucr:CuCu----CuCu` |
| 51 | rotate | 50 | 5 | `Cu----CucrCu:cr----Cucrcr:Cu----CuCuCu:Cu----CucrCu:Cu----CuCuCu` |
| 52 | cut | 51 | 1 | `------Cu--Cu:------Cu----:------CuCuCu:------CucrCu:------CuCuCu` |
| 53 | rotate | 52 | 1 | `Cu------Cu--:--------Cu--:Cu------CuCu:Cu------Cucr:Cu------CuCu` |
| 54 | cut | 53 | 1 | `--------Cu--:--------Cu--:--------CuCu:--------Cucr:--------CuCu` |
| 55 | base | — | — | `CuCuCu------` |
| 56 | base | — | — | `CuCuCu------` |
| 57 | stack | 55, 56 | — | `CuCuCu------:CuCuCu------` |
| 58 | base | — | — | `CuCuCu------` |
| 59 | stack | 57, 58 | — | `CuCuCu------:CuCuCu------:CuCuCu------` |
| 60 | base | — | — | `CuCuCu------` |
| 61 | stack | 59, 60 | — | `CuCuCu------:CuCuCu------:CuCuCu------:CuCuCu------` |
| 62 | base | — | — | `CuCuCu------` |
| 63 | stack | 61, 62 | — | `CuCuCu------:CuCuCu------:CuCuCu------:CuCuCu------:CuCuCu------` |
| 64 | swap | 54, 63 | 1 | `CuCuCu--Cu--:CuCuCu--Cu--:CuCuCu--CuCu:CuCuCu--Cucr:CuCuCu--CuCu` |
| 65 | rotate | 64 | 1 | `--CuCuCu--Cu:--CuCuCu--Cu:CuCuCuCu--Cu:crCuCuCu--Cu:CuCuCuCu--Cu` |
| 66 | cut | 65 | 0 | `--CuCu------:--CuCu------:CuCuCu------:crCuCu------:CuCuCu------` |
| 67 | swap | 22, 66 | 1 | `--CuCu--Cu--:--CuCu--Cu--:CuCuCu--CuCu:crCuCu--Cu--:CuCuCu--CuCu` |
| 68 | rotate | 67 | 1 | `----CuCu--Cu:----CuCu--Cu:CuCuCuCu--Cu:--crCuCu--Cu:CuCuCuCu--Cu` |
| 69 | cut | 68 | 0 | `----Cu------:----Cu------:CuCuCu------:--crCu------:CuCuCu------` |
| 70 | base | — | — | `CuCuCuCuCuP-` |
| 71 | base | — | — | `CuCuCuCuCuCu` |
| 72 | stack | 70, 71 | — | `CuCuCuCuCuP-:CuCuCuCuCuCu` |
| 73 | base | — | — | `CuCuCuCuCuP-` |
| 74 | stack | 72, 73 | — | `CuCuCuCuCuP-:CuCuCuCuCuCu:CuCuCuCuCuP-` |
| 75 | base | — | — | `CuCuCuCuCuP-` |
| 76 | stack | 74, 75 | — | `CuCuCuCuCuP-:CuCuCuCuCuCu:CuCuCuCuCuP-:CuCuCuCuCuP-` |
| 77 | base | — | — | `CuCuCuCuCuP-` |
| 78 | stack | 76, 77 | — | `CuCuCuCuCuP-:CuCuCuCuCuCu:CuCuCuCuCuP-:CuCuCuCuCuP-:CuCuCuCuCuP-` |
| 79 | crystal | 78 | r | `CuCuCuCuCucr:CuCuCuCuCuCu:CuCuCuCuCucr:CuCuCuCuCucr:CuCuCuCuCucr` |
| 80 | cut | 79 | 1 | `------CuCucr:------CuCuCu:------CuCucr:------CuCucr:------CuCucr` |
| 81 | rotate | 80 | 1 | `cr------CuCu:Cu------CuCu:cr------CuCu:cr------CuCu:cr------CuCu` |
| 82 | cut | 81 | 0 | `cr----------:Cu----------:cr----------:cr----------:cr----------` |
| 83 | base | — | — | `----------Cu` |
| 84 | base | — | — | `----------P-` |
| 85 | stack | 83, 84 | — | `----------Cu:----------P-` |
| 86 | base | — | — | `----------Cu` |
| 87 | stack | 85, 86 | — | `----------Cu:----------P-:----------Cu` |
| 88 | base | — | — | `----------Cu` |
| 89 | stack | 87, 88 | — | `----------Cu:----------P-:----------Cu:----------Cu` |
| 90 | base | — | — | `----------Cu` |
| 91 | stack | 89, 90 | — | `----------Cu:----------P-:----------Cu:----------Cu:----------Cu` |
| 92 | swap | 82, 91 | 0 | `cr--------Cu:Cu--------P-:cr--------Cu:cr--------Cu:cr--------Cu` |
| 93 | rotate | 92 | 5 | `--------Cucr:--------P-Cu:--------Cucr:--------Cucr:--------Cucr` |
| 94 | base | — | — | `CuP-P-CuCuCu` |
| 95 | crystal | 94 | r | `CucrcrCuCuCu` |
| 96 | cut | 95 | 0 | `Cucrcr------` |
| 97 | rotate | 96 | 5 | `crcr------Cu` |
| 98 | cut | 97 | 0 | `crcr--------` |
| 99 | base | — | — | `CuCu--------` |
| 100 | stack | 98, 99 | — | `crcr--------:CuCu--------` |
| 101 | base | — | — | `CuCu--------` |
| 102 | stack | 100, 101 | — | `crcr--------:CuCu--------:CuCu--------` |
| 103 | base | — | — | `CuCu--------` |
| 104 | stack | 102, 103 | — | `crcr--------:CuCu--------:CuCu--------:CuCu--------` |
| 105 | base | — | — | `CuCu--------` |
| 106 | stack | 104, 105 | — | `crcr--------:CuCu--------:CuCu--------:CuCu--------:CuCu--------` |
| 107 | swap | 93, 106 | 1 | `crcr----Cucr:CuCu----P-Cu:CuCu----Cucr:CuCu----Cucr:CuCu----Cucr` |
| 108 | rotate | 107 | 5 | `cr----Cucrcr:Cu----P-CuCu:Cu----CucrCu:Cu----CucrCu:Cu----CucrCu` |
| 109 | cut | 108 | 1 | `------CuCuCu:------P-----:------CucrCu:------CucrCu:------CucrCu` |
| 110 | rotate | 109 | 1 | `Cu------CuCu:--------P---:Cu------Cucr:Cu------Cucr:Cu------Cucr` |
| 111 | cut | 110 | 1 | `--------CuCu:--------P---:--------Cucr:--------Cucr:--------Cucr` |
| 112 | swap | 111, 69 | 1 | `----Cu--CuCu:----Cu--P---:CuCuCu--Cucr:--crCu--Cucr:CuCuCu--Cucr` |
| 113 | rotate | 112 | 1 | `Cu----Cu--Cu:------Cu--P-:crCuCuCu--Cu:cr--crCu--Cu:crCuCuCu--Cu` |
| 114 | cut | 113 | 0 | `Cu----------:------------:crCuCu------:cr--cr------:crCuCu------` |
| 115 | base | — | — | `--Cu--------` |
| 116 | base | — | — | `--Cu--------` |
| 117 | stack | 115, 116 | — | `--Cu--------:--Cu--------` |
| 118 | base | — | — | `--CuCu------` |
| 119 | stack | 117, 118 | — | `--Cu--------:--Cu--------:--CuCu------` |
| 120 | base | — | — | `--Cu--------` |
| 121 | stack | 119, 120 | — | `--Cu--------:--Cu--------:--CuCu------:--Cu--------` |
| 122 | base | — | — | `--CuCu------` |
| 123 | stack | 121, 122 | — | `--Cu--------:--Cu--------:--CuCu------:--Cu--------:--CuCu------` |
| 124 | base | — | — | `------CuCu--` |
| 125 | base | — | — | `------CuCu--` |
| 126 | stack | 124, 125 | — | `------CuCu--:------CuCu--` |
| 127 | base | — | — | `------CuCu--` |
| 128 | stack | 126, 127 | — | `------CuCu--:------CuCu--:------CuCu--` |
| 129 | base | — | — | `------CuCu--` |
| 130 | stack | 128, 129 | — | `------CuCu--:------CuCu--:------CuCu--:------CuCu--` |
| 131 | base | — | — | `------CuCu--` |
| 132 | stack | 130, 131 | — | `------CuCu--:------CuCu--:------CuCu--:------CuCu--:------CuCu--` |
| 133 | swap | 123, 132 | 0 | `--Cu--CuCu--:--Cu--CuCu--:--CuCuCuCu--:--Cu--CuCu--:--CuCuCuCu--` |
| 134 | rotate | 133 | 5 | `Cu--CuCu----:Cu--CuCu----:CuCuCuCu----:Cu--CuCu----:CuCuCuCu----` |
| 135 | cut | 134 | 0 | `Cu--Cu------:Cu--Cu------:CuCuCu------:Cu--Cu------:CuCuCu------` |
| 136 | rotate | 135 | 1 | `--Cu--Cu----:--Cu--Cu----:--CuCuCu----:--Cu--Cu----:--CuCuCu----` |
| 137 | cut | 136 | 0 | `--Cu--------:--Cu--------:--CuCu------:--Cu--------:--CuCu------` |
| 138 | base | — | — | `CuCuP-CuCuCu` |
| 139 | base | — | — | `CuCuP-CuCuCu` |
| 140 | stack | 138, 139 | — | `CuCuP-CuCuCu:CuCuP-CuCuCu` |
| 141 | base | — | — | `CuCuCuCuCuCu` |
| 142 | stack | 140, 141 | — | `CuCuP-CuCuCu:CuCuP-CuCuCu:CuCuCuCuCuCu` |
| 143 | base | — | — | `CuCuP-CuCuCu` |
| 144 | stack | 142, 143 | — | `CuCuP-CuCuCu:CuCuP-CuCuCu:CuCuCuCuCuCu:CuCuP-CuCuCu` |
| 145 | crystal | 144 | r | `CuCucrCuCuCu:CuCucrCuCuCu:CuCuCuCuCuCu:CuCucrCuCuCu` |
| 146 | cut | 145 | 0 | `CuCucr------:CuCucr------:CuCuCu------:CuCucr------` |
| 147 | rotate | 146 | 5 | `Cucr------Cu:Cucr------Cu:CuCu------Cu:Cucr------Cu` |
| 148 | cut | 147 | 0 | `Cucr--------:Cucr--------:CuCu--------:Cucr--------` |
| 149 | rotate | 148 | 1 | `--Cucr------:--Cucr------:--CuCu------:--Cucr------` |
| 150 | base | — | — | `--CuCu------` |
| 151 | stack | 149, 150 | — | `--Cucr------:--Cucr------:--CuCu------:--Cucr------:--CuCu------` |
| 152 | base | — | — | `CuCuCuCuCuCu` |
| 153 | base | — | — | `CuCuCuCuP-P-` |
| 154 | stack | 152, 153 | — | `CuCuCuCuCuCu:CuCuCuCuP-P-` |
| 155 | crystal | 154 | r | `CuCuCuCuCuCu:CuCuCuCucrcr` |
| 156 | cut | 155 | 1 | `------CuCuCu:------Cucrcr` |
| 157 | rotate | 156 | 5 | `----CuCuCu--:----Cucrcr--` |
| 158 | cut | 157 | 1 | `------CuCu--:------crcr--` |
| 159 | base | — | — | `------CuCu--` |
| 160 | stack | 158, 159 | — | `------CuCu--:------crcr--:------CuCu--` |
| 161 | base | — | — | `------CuCu--` |
| 162 | stack | 160, 161 | — | `------CuCu--:------crcr--:------CuCu--:------CuCu--` |
| 163 | base | — | — | `------CuCu--` |
| 164 | stack | 162, 163 | — | `------CuCu--:------crcr--:------CuCu--:------CuCu--:------CuCu--` |
| 165 | swap | 151, 164 | 0 | `--CucrCuCu--:--Cucrcrcr--:--CuCuCuCu--:--CucrCuCu--:--CuCuCuCu--` |
| 166 | rotate | 165 | 5 | `CucrCuCu----:Cucrcrcr----:CuCuCuCu----:CucrCuCu----:CuCuCuCu----` |
| 167 | cut | 166 | 0 | `Cu--Cu------:Cu----------:CuCuCu------:CucrCu------:CuCuCu------` |
| 168 | rotate | 167 | 1 | `--Cu--Cu----:--Cu--------:--CuCuCu----:--CucrCu----:--CuCuCu----` |
| 169 | cut | 168 | 0 | `--Cu--------:--Cu--------:--CuCu------:--Cucr------:--CuCu------` |
| 170 | base | — | — | `------CuCuCu` |
| 171 | base | — | — | `------CuCuCu` |
| 172 | stack | 170, 171 | — | `------CuCuCu:------CuCuCu` |
| 173 | base | — | — | `------CuCuCu` |
| 174 | stack | 172, 173 | — | `------CuCuCu:------CuCuCu:------CuCuCu` |
| 175 | base | — | — | `------CuCuCu` |
| 176 | stack | 174, 175 | — | `------CuCuCu:------CuCuCu:------CuCuCu:------CuCuCu` |
| 177 | base | — | — | `------CuCuCu` |
| 178 | stack | 176, 177 | — | `------CuCuCu:------CuCuCu:------CuCuCu:------CuCuCu:------CuCuCu` |
| 179 | swap | 169, 178 | 0 | `--Cu--CuCuCu:--Cu--CuCuCu:--CuCuCuCuCu:--CucrCuCuCu:--CuCuCuCuCu` |
| 180 | rotate | 179 | 1 | `Cu--Cu--CuCu:Cu--Cu--CuCu:Cu--CuCuCuCu:Cu--CucrCuCu:Cu--CuCuCuCu` |
| 181 | cut | 180 | 1 | `--------CuCu:--------CuCu:------CuCuCu:------crCuCu:------CuCuCu` |
| 182 | swap | 137, 181 | 0 | `--Cu----CuCu:--Cu----CuCu:--CuCuCuCuCu:--Cu--crCuCu:--CuCuCuCuCu` |
| 183 | rotate | 182 | 1 | `Cu--Cu----Cu:Cu--Cu----Cu:Cu--CuCuCuCu:Cu--Cu--crCu:Cu--CuCuCuCu` |
| 184 | cut | 183 | 1 | `----------Cu:----------Cu:------CuCuCu:--------crCu:------CuCuCu` |
| 185 | base | — | — | `CuCuP-CuCuCu` |
| 186 | base | — | — | `CuCuCuCuCuCu` |
| 187 | stack | 185, 186 | — | `CuCuP-CuCuCu:CuCuCuCuCuCu` |
| 188 | base | — | — | `CuCuP-CuCuCu` |
| 189 | stack | 187, 188 | — | `CuCuP-CuCuCu:CuCuCuCuCuCu:CuCuP-CuCuCu` |
| 190 | base | — | — | `CuCuP-CuCuCu` |
| 191 | stack | 189, 190 | — | `CuCuP-CuCuCu:CuCuCuCuCuCu:CuCuP-CuCuCu:CuCuP-CuCuCu` |
| 192 | base | — | — | `CuCuP-CuCuCu` |
| 193 | stack | 191, 192 | — | `CuCuP-CuCuCu:CuCuCuCuCuCu:CuCuP-CuCuCu:CuCuP-CuCuCu:CuCuP-CuCuCu` |
| 194 | crystal | 193 | r | `CuCucrCuCuCu:CuCuCuCuCuCu:CuCucrCuCuCu:CuCucrCuCuCu:CuCucrCuCuCu` |
| 195 | cut | 194 | 0 | `CuCucr------:CuCuCu------:CuCucr------:CuCucr------:CuCucr------` |
| 196 | rotate | 195 | 1 | `--CuCucr----:--CuCuCu----:--CuCucr----:--CuCucr----:--CuCucr----` |
| 197 | cut | 196 | 1 | `------cr----:------Cu----:------cr----:------cr----:------cr----` |
| 198 | base | — | — | `----Cu------` |
| 199 | base | — | — | `----P-------` |
| 200 | stack | 198, 199 | — | `----Cu------:----P-------` |
| 201 | base | — | — | `----Cu------` |
| 202 | stack | 200, 201 | — | `----Cu------:----P-------:----Cu------` |
| 203 | base | — | — | `----Cu------` |
| 204 | stack | 202, 203 | — | `----Cu------:----P-------:----Cu------:----Cu------` |
| 205 | base | — | — | `----Cu------` |
| 206 | stack | 204, 205 | — | `----Cu------:----P-------:----Cu------:----Cu------:----Cu------` |
| 207 | swap | 197, 206 | 1 | `----Cucr----:----P-Cu----:----Cucr----:----Cucr----:----Cucr----` |
| 208 | rotate | 207 | 5 | `--Cucr------:--P-Cu------:--Cucr------:--Cucr------:--Cucr------` |
| 209 | base | — | — | `CuCuCuCuP-P-` |
| 210 | crystal | 209 | r | `CuCuCuCucrcr` |
| 211 | cut | 210 | 1 | `------Cucrcr` |
| 212 | rotate | 211 | 5 | `----Cucrcr--` |
| 213 | cut | 212 | 1 | `------crcr--` |
| 214 | base | — | — | `------CuCu--` |
| 215 | stack | 213, 214 | — | `------crcr--:------CuCu--` |
| 216 | base | — | — | `------CuCu--` |
| 217 | stack | 215, 216 | — | `------crcr--:------CuCu--:------CuCu--` |
| 218 | base | — | — | `------CuCu--` |
| 219 | stack | 217, 218 | — | `------crcr--:------CuCu--:------CuCu--:------CuCu--` |
| 220 | base | — | — | `------CuCu--` |
| 221 | stack | 219, 220 | — | `------crcr--:------CuCu--:------CuCu--:------CuCu--:------CuCu--` |
| 222 | swap | 208, 221 | 0 | `--Cucrcrcr--:--P-CuCuCu--:--CucrCuCu--:--CucrCuCu--:--CucrCuCu--` |
| 223 | rotate | 222 | 5 | `Cucrcrcr----:P-CuCuCu----:CucrCuCu----:CucrCuCu----:CucrCuCu----` |
| 224 | cut | 223 | 0 | `CuCuCu------:P-----------:CucrCu------:CucrCu------:CucrCu------` |
| 225 | rotate | 224 | 1 | `--CuCuCu----:--P---------:--CucrCu----:--CucrCu----:--CucrCu----` |
| 226 | cut | 225 | 0 | `--CuCu------:--P---------:--Cucr------:--Cucr------:--Cucr------` |
| 227 | swap | 226, 184 | 0 | `--CuCu----Cu:--P-------Cu:--CucrCuCuCu:--Cucr--crCu:--CucrCuCuCu` |
| 228 | rotate | 227 | 1 | `Cu--CuCu----:Cu--P-------:Cu--CucrCuCu:Cu--Cucr--cr:Cu--CucrCuCu` |
| 229 | cut | 228 | 1 | `------Cu----:------------:------crCuCu:------cr--cr:------crCuCu` |
| 230 | swap | 114, 229 | 0 | `Cu----Cu----:------------:crCuCucrCuCu:cr--crcr--cr:crCuCucrCuCu` |
