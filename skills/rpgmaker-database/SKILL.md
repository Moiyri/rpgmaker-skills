---
name: rpgmaker-database
description: 读取和修改 RPG Maker MV/MZ 工程数据库的任意 JSON 字段；任何数据库修改都触发，包括标准数据库、System、地图、事件指令、备注与插件自定义 JSON 数据。支持任意对象或数组路径及多层 JSON 字符串字段，所有写入必须通过随附脚本完成。plugins.js 使用插件清单 skill，存档不默认属于工程数据库。
---

# RPG Maker 数据库

对数据库的任何修改都使用此 skill，不因字段未登记、位于地图/事件中或属于插件自定义数据而绕过。使用本 skill 的 `scripts/database.py` 读取、预览、写入与恢复；禁止直接编辑目标 JSON、apply_patch、文本替换或另写临时脚本覆盖数据库。可以编写独立操作计划，测试夹具的创建不受此限制。

## 定位与读取

读取项目约定，明确数据库根目录。标准数据库通常以 `<project>/data` 为根；自定义数据可以显式选择其所在目录，不假定工程所有 JSON 都是数据库。路径仅能指向该根目录内的现有 `.json` 文件，不跟随内部符号链接。

`<skill>` 是本 `SKILL.md` 所在目录，不是项目目录：

```sh
python3 "<skill>/scripts/database.py" --root "<project>/data" inspect --file "Actors.json" --summary
python3 "<skill>/scripts/database.py" --root "<project>/data" inspect --file "Actors.json" --path '[3]' --children
python3 "<skill>/scripts/database.py" --root "<project>/data" inspect --file "Actors.json" --path '[3,"traits",0,"value"]'
```

数字路径项表示数组下标，字符串表示对象键。先检查记录的实际 `id`，不能仅根据名称猜测 ID。`--children` 列出下一层路径；字符串可显示 `json_decodable` 与显式解码路径。自动显示可解码性不代表应该解码，按插件格式决定是否使用 `{"decode":"json"}`。复杂路径写入独立文件并使用 `--path-file`，避免 shell 转义错误。

## 任意字段修改

先阅读 [脚本接口](references/script-contract.md)。用 JSON 计划精确指定文件、路径、操作和值：

- `set`：替换已有值，包括根值、对象、数组、事件指令和任意层级的字段。
- `put`：新增对象字段，不覆盖已有字段，不自动创建缺失的中间路径。
- `remove`：删除对象字段；对数组槽位写入 `null`，不前移后续 ID。
- `splice`：显式插入、删除或替换连续数组元素，会改变后续下标。
- `test`：断言原值，整批操作任一步不符均停止。

路径没有字段白名单，脚本也不强制保持旧字段类型；计划中的 JSON 类型就是目标类型。按需求明确选择，不把字符串数字默认为数字。嵌套 JSON 字符串在路径中逐层添加 `{"decode":"json"}`，让正式脚本解码、修改、重新编码，无需 agent 重写整个参数字符串。不执行脚本、公式或插件命令的内容。

修改 ID 数组时通常使用 `set` 或 `remove` 保持槽位。只有任务确实要求移动/压缩数组时才使用 `splice`。修改 ID、引用、地图尺寸/图块、事件指令及分支结构时，核对相关数据并在同一计划中完成必要的关联修改。脚本支持这些字段的读写，但不自动修复引用、事件缩进、控制流或地图尺寸关系。

## 预览与写入

```sh
python3 "<skill>/scripts/database.py" --root "<project>/data" apply --plan "<plan.json>"
python3 "<skill>/scripts/database.py" --root "<project>/data" apply --plan "<plan.json>" --write --expect-preview "<preview_sha256>"
```

检查预览中的字段路径、前后值摘要和涉及文件。大型值摘要会截断，使用 `inspect` 读取完整值或核对操作计划。写入使用预览返回的 `preview_sha256`，它同时绑定源文件与计划；不要在预览后变更计划。源文件或计划冲突时重新读取并核对意图，不只替换指纹重试。

对用户已经授权的修改正常执行，无需增加一次常规确认。避免编辑器同时保存数据库。脚本执行全批内存校验、备份及逐文件原子替换；多文件失败会尝试回滚，细节见接口文档。若报告 `recovery_required`，先检查事务日志和当前内容，不继续盲目写入。

写入后用 `inspect` 核对目标字段和必要的关联字段，记录返回的事务清单路径，按项目约定更新变更记录。`validate` 仅表示 JSON 语法有效；游戏数据关系与运行行为需单独核查，不把文件写入成功当成 Playtest 通过。

## 恢复

```sh
python3 "<skill>/scripts/database.py" --root "<project>/data" restore --transaction "<transaction.json>"
python3 "<skill>/scripts/database.py" --root "<project>/data" restore --transaction "<transaction.json>" --write --expect-preview "<preview_sha256>"
```

恢复覆盖该事务涉及的整份文件，先核对预览以避免撤销后来需要保留的修改。恢复也通过脚本完成，并为恢复前状态新建事务备份。
