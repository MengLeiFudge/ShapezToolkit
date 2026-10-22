# 旧 XianYu 存档

这里保存此前称为 `TMAM-XianYu` 的旧机器记录，存档 ID 为 `72b2f5b7adb052ae84aa78fb4050371107d32eb5`。它与 [XianYu-20221129](../xianyu_20221129/README.md) 是不同存档，也不能按名称猜测为 Nabi。

已有全量记录中，48,432 个可制作结构成功 46,961 个，漏解 1,471 个；其中 955 个稳定在错误结果，516 个进入周期。详细数据保存在本机 `verification/20261021/`：`XianYu.csv`、`XianYu-differences.csv`、`XianYu-circuit.json` 和各进程分段文件。不纳入 Git。

与 BugFix 的历史比较报告在上级本机 `comparison/20261021/REPORT.md`。此次只归类已有资料，没有修改旧机器或重新验证。

`tmam verify --machine XianYu` 仍使用原存档 ID。本机原 `.bin` 目前仅保留 `.bin.backup`，重新执行前需自行准备原文件；工具不会把备份或其他机器静默代入。
