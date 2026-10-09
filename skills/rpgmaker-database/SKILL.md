---
name: rpgmaker-database
description: 读取和修改 RPG Maker MV/MZ 工程数据库的任意 JSON 字段；任何数据库修改都触发，包括标准数据库、System、地图、事件指令、备注与插件自定义 JSON 数据。支持任意对象或数组路径及多层 JSON 字符串字段，所有写入必须通过随附脚本完成。plugins.js 使用插件清单 skill，存档不默认属于工程数据库。
---

# RPG Maker 数据库

对数据库的任何修改都使用此 skill，不因字段未登记、位于地图/事件中或属于插件自定义数据而绕过。使用本 skill 的 `scripts/database.py` 读取、预览、写入与恢复；禁止直接编辑目标 JSON、apply_patch、文本替换或另写临时脚本覆盖数据库。可以编写独立操作计划，测试夹具的创建不受此限制。

## 物品对象接口

修改物品优先使用 `scripts/database_api.py` 的 `Database` 对象，无需手写 JSON 计划。先阅读 [物品接口](references/item-api.md) 与 [入门示例](examples/items.py)：列出／搜索物品，使用 create／clear 创建和清空，使用 references 查询引用，按 ID 获取后修改属性、伤害及使用效果，调用 `preview()` 核对，再 `commit(preview)`。该接口通过正式 `database.py` 后端写入和备份，不直接覆盖工程文件。未知字段与效果保留，未封装的操作仍使用下述通用脚本。

## 地图管理

`db.maps.list/find/get/tree` 查询地图目录与属性，create/delete 创建删除地图，地图对象 resize 调整大小，名称、父级和地图属性通过对象编辑，详见[地图接口](references/maps-api.md)。地图事件与指令由事件技能处理；图块绘制及遇敌列表暂不提供编辑接口。创建须目录编号和文件均未占用，禁止覆盖；缩小或删除遇到静态引用冲突时停止。父级禁止循环，图块集变更检查引用；提交保留事件和图块数据。

## 开关与变量

`db.switches`、`db.variables` 支持 list/find/get/set/clear，负责编号名称，见[接口说明](references/switch-variables-api.md)。清空仅移除名称，不重置运行值、不删除引用。ON/OFF 和变量赋值由事件技能编写指令。空名称不代表未使用，不据此自动复用编号。

## 公共事件条目

`db.common_events.list/find/create/delete` 负责公共事件条目管理，见[接口说明](references/common-events-api.md)。创建后提交并将工程路径、返回 ID 交给[事件技能](../rpgmaker-events/SKILL.md)；名称、触发设置及具体指令编辑由事件技能负责。不要通过数据库对象直接修改指令列表。delete 清空整条记录、保留编号；仅清空指令使用事件技能。

## 角色对象接口

角色操作使用 `Database.actors`：list／find／get／create／clear／references。字段、初始装备与特性用法见 [角色接口](references/actor-api.md) 和 [示例](examples/actors.py)。角色与物品共用预览及提交。装备适用性、素材和插件动态引用尚不自动校验。

## System（系统）

统一使用 `db.system`，不区分 system1/system2。覆盖编辑器 System 1 和 System 2：标题、初始队伍、窗口颜色、载具、出生点、战斗模式、选项、音乐和音效，以及菜单分类、侧视动作、尺寸、编辑器和高级设置。见[系统接口](references/system-api.md)及[示例](examples/system.py)。清空通过对应 clear 方法完成，不删除必需字段；与 Types 共用快照及事务。

## Terms（用语）

使用 `db.terms.basic / params / commands / messages` 查询与修改用语。先 list 查看编号或消息键，再 set；clear 清空文本，保留编号和 null 保留位。消息替换符按用途保留，详见[用语接口](references/terms-api.md)与[示例](examples/terms.py)。与 Types、System 共用预览提交。

## Types（类型）

使用 `db.types.elements / skill_types / weapon_types / armor_types / equipment_types`，对应编辑器 Types 页的五列。支持 list／find／get／set／add／clear，详见[类型接口](references/types-api.md)。修改与角色、物品共用 preview／commit。

编号先从对应列表查询，不凭经验猜测。固定能力及标记见[引擎固定编号](references/engine-enums.md)；尚未封装的技能、状态列表使用正式数据库脚本 inspect。没有统一的 lookup 入口。

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
