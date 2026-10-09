# Veloria 多层嵌套参数验证

日期：2026-10-07。仅读取原工程，在临时副本上测试；未运行游戏或插件代码。

## 输入

- 原文件：`/Users/moiyri/Game/Veloria/veloria-main/js/plugins.js`
- 工程标识：RPGMZ 1.10.0
- 文件大小：1,396,735 字节
- SHA-256：`0e278b94e6e9a8b0ac16dd36602b49160bd34f7588d06bc1f9183d22d4cddc17`
- 57 个插件、604 个顶层参数；58 个参数存在至少两次 JSON 解码路径，最深 6 次。

解码层数指从参数字符串出发沿一条路径执行 `json.loads` 的次数，包含数字、布尔值、带引号文本的解码，不等同于对象或数组的结构深度。这里的自动解码只用于测试数据探测，不作为正式脚本推断插件参数类型的规则。

## 方法

通过正式 CLI `inspect` 读取副本，并与独立的标准库 JSON 读取结果逐项对比。对全部 58 个多层参数，各选一条最深路径上的末端字段，另选 1 个普通文本参数，生成 JSON 操作计划，通过正式脚本执行预览和写入。实际涉及 14 个插件、59 个参数。

部分实际测试路径（省略各节点间的 JSON 解码步骤）：

| 插件 | 参数及内部路径 | 解码次数 |
| --- | --- | --- |
| `Ve_2_DressUp` | `actorConfigs[0].outfits[0].standingPictureMappings[0].baseId` | 6 |
| `Liy_Graphics` | `mapLayerSetting[0].layers[0].x` | 5 |
| `VisuMZ_0_CoreEngine` | `MenuLayout:struct → GameEnd:struct → CommandList:arraystruct[0] → TextJS:func` | 5 |
| `VisuMZ_1_OptionsCore` | `Categories:arraystruct[0] → List:arraystruct[0] → Icon:num` | 5 |
| `TAA_BookMenu` | `Plugin Manager Books → Books[0] → Visible Text List[0]` | 5 |

文本测试值附加中文、换行、引号、反斜杠和 emoji；数字加一、布尔值翻转。测试值仅用于验证序列化，不代表有效游戏配置，不执行其内容。

## 结果

- 读取结果与独立 JSON 解析一致。
- 59 个参数的目标末端字段均修改成功；逐层比较确认同级字段保持原值，包括同级的编码字符串。
- 其余 545 个顶层参数字符串逐一完全一致。
- 插件顺序、启停、名称、描述及其他非参数字段均保持一致。
- 预览未修改文件或创建备份。
- 写入前备份与原文件字节完全一致。
- 修改后的副本通过 Node.js `--check`。
- 重复执行同一计划不重写、不新增备份。
- 旧指纹被拒绝；整批计划包含非法参数类型时不发生部分写入。
- 通过正式脚本恢复后，副本与原文件字节完全一致。
- 测试结束再次核对原文件，SHA-256 未变。
- 原有测试套件使用 Veloria 作为真实工程输入，18 项测试全部通过。

## 能力边界

正式脚本准确读取和保留的是参数的原始字符串，可安全写入重新编码后的参数字符串。目前没有 `参数路径 → 深层字段` 的直接修改接口：测试程序负责逐层解码、选择末端字段、重新编码并生成计划，正式脚本负责验证与写入。这次验证证明这种流程适用于本工程的复杂参数，不代表脚本已能自动理解嵌套参数含义，也不覆盖全部末端字段或游戏运行行为。

## 复现与产物

```sh
python3 tests/probe_nested_project.py /path/to/project/js/plugins.js
RPGMAKER_TEST_PROJECT=/path/to/project python3 -m unittest discover -s tests -v
```

探针自动创建临时目录，保留 `plan.json`、修改后副本 `modified-evidence.js`、经脚本恢复的 `plugins.js`、备份与 `report.json`。工程配置及参数内容不写入仓库。

本次产物目录：`/var/folders/_4/b6ybf2797nb9g6wvkx97r1r40000gn/T/rpgmaker-nested-probe-flvn472v`。临时目录可能被系统清理；本文保留验证结论，测试程序可重新生成证据。
