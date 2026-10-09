---
name: rpgmaker-events
description: 查询、编写和修改 RPG Maker MZ 公共事件指令及地图事件。需要全局按名称或开关变量搜索、创建删除地图事件、编辑名称备注、事件页条件图像移动触发设置、页面管理或指令增删改查时使用；通过正式脚本预览写回。其他数据库字段使用 rpgmaker-database，plugins.js 使用 rpgmaker-plugins。
---

# RPG Maker 事件编写器

使用 `scripts/event_api.py` 的对象接口维护指令，使用 `scripts/events.py` 管理事件指令，使用 `scripts/map_events.py` 管理整个地图事件、事件页和全局引用搜索。禁止直接编辑工程 JSON、文本替换或另写脚本覆盖目标数据库。可以写调用接口的 Python 程序和独立计划文件。

编写事件前阅读[最佳实践](references/best-practices.md)。标签使用可读语言，可用中文；英文首字母大写，词间用空格，不用下划线或连字符。事件转向可用于分阶段动画，阶段间通常等待 3 帧；踏步用于静止循环动画，具体帧布局以素材为准。灯台、书、盆栽等没有转向动画的物件应开启固定朝向，避免交互时显示错误图案。临时图片使用完成后必须消除；渐显渐隐按最佳实践的顺序编写。Note 默认留空或保留原值，仅用于明确的插件标签等特殊用途；逻辑说明使用 Comment 指令。地图事件名称保持简短；公共事件中文命名为 `事件ID:【类别】事件名`，英文为 `事件ID:<Category>Event Name`；ID 至少三位补零。

## 依赖与接口

Python 3.10+，仅标准库。必须同时分发相邻的 `../rpgmaker-database/`，保留两个 skill 的目录结构；写入和恢复由其正式 `scripts/database.py` 承担。执行工程修改前阅读[数据库 skill](../rpgmaker-database/SKILL.md)。依赖缺失时先补齐，不绕过后端写文件。

`<skill>` 表示本文件所在目录，`<project>` 表示含 data、js 的工程根目录。

先查看[指令实现状态](references/command-status.md)，不要把原始块保留当作支持语义编辑。具体参数使用源码 docstring，通过 `help()` 或在 scripts 目录执行 `python3 -m pydoc event_api` 查询。

指令实现集中在 `event_core/commands/`，内部按引擎分类；统一从 `event_api` 导入。地图事件管理、查询和编解码模块位于 `event_core/`，与指令目录分开。

- [message.py](scripts/event_core/commands/message.py)：消息（ShowText）。
- [game_progression.py](scripts/event_core/commands/game_progression.py)：游戏进程（开关、变量、独立开关、计时器）。
- [flow_control.py](scripts/event_core/commands/flow_control.py)：流程控制（条件、循环、公共事件、注释）。
- [party.py](scripts/event_core/commands/party.py)：队伍（金币、物品）。
- [picture.py](scripts/event_core/commands/picture.py)：图片（显示、移动、旋转、色调、消除）；[临时图片渐显渐隐示例](examples/picture.py)。
- [timing.py](scripts/event_core/commands/timing.py)：计时（Wait）。
- [map_commands.py](scripts/event_core/commands/map_commands.py)：地图指令（EraseEvent）。
- [screen.py](scripts/event_core/commands/screen.py)：画面（淡入淡出、色调、闪光、震动、天气）。
- [audio_video.py](scripts/event_core/commands/audio_video.py)：音频与视频（播放、淡出、保存／重播 BGM、停止 SE、影片）。
- [scene_control.py](scripts/event_core/commands/scene_control.py)：场景控制（名字输入、菜单、存档、游戏结束、返回标题）。
- [advanced.py](scripts/event_core/commands/advanced.py)：高级（Script、PluginCommand）。
- [opaque.py](scripts/event_core/commands/opaque.py)：原始指令块保留。
- [movement.py](scripts/event_core/commands/movement.py)：Movement 指令和 Route 步骤；[入门示例](examples/movement.py)。
- [conditions.py](scripts/event_core/conditions.py)：条件构造方法。
- [operands.py](scripts/event_core/operands.py)：操作数；Game Data 使用 ScriptValue 表达式读取。
- [map_events.py](scripts/event_core/map_events.py)：MapDocument、MapEvent、EventPage，读取和维护地图事件与页面。
- [event_search.py](scripts/event_core/event_search.py)：按事件名、开关／变量 ID 全局搜索，列出地图事件。
- [物品使用公共事件](examples/item_common_event.py)：位置及有效性检查、特殊误用提示、失败标签、成功后可选扣除物品。
- [门事件](examples/door.py)：创建确定键交互的门，可用解锁开关区分锁门／开门页；平时固定朝向，动画时临时解除，随后玩家前进、传送；命名为 门（目的）或 Door（目的）。
- [一次性物品拾取](examples/one_time_pickup.py)：从创建事件开始，闪光动画、获得物品、独立开关 A、空白隐藏页。
- [地图编辑示例](examples/map_event.py)：修改名称、编辑第一页并复制条件页。
- [event_list.py](scripts/event_core/event_list.py)：列表增删改查、编译和计划导出。
- [公共事件 165 示例](examples/common165.py)：嵌套条件与循环，输出整段替换计划。
- [公共事件 167 示例](examples/common167.py)：角色入队判断，输出追加计划。

示例编号只是示例，实际操作必须使用用户指定的目标。

编写插件命令前，先使用 [插件技能](../rpgmaker-plugins/SKILL.md) 的 check 检查文件、注册及启用状态；同一工程同一插件本轮检查一次，配置改变后重新检查。缺失或禁用时报告，不自动启用。随后调用 `plugin_help(project, "插件名")`，或执行：

```sh
python3 "<skill>/scripts/events.py" --project "<project>" plugin-help --plugin "veloria/Ve_1_Message"
```

返回简短纯文本，默认每条命令一行，包含命令 ID、显示名和参数默认值；隐藏已识别的 Separator 分隔项，不输出整份帮助。用 `plugin_help(project, plugin, command="命令ID")` 或 CLI `--command 命令ID` 查看完整参数用法、类型、选项与限制。配置参数用 `section="parameters"`／`--section parameters`，结构体用 `struct="名称"`／`--struct 名称`，完整帮助用 `section="help"`／`--section help`。概要中的长默认值会省略，编写前查询命令详情取得完整值。

默认优先中文，可用 `--language` 指定语言；同名插件需指定子目录。无需 agent 手工阅读源码。缺少声明或有重复项时会提示，不猜测未知参数；查询结果不证明插件启用或运行时注册有效。

根据查询结果创建 `PluginCommand(plugin, command, args, display_name=None, argument_labels=None)`，使用返回的插件路径、命令 ID、参数名和显示标签；按需使用声明的 default，不补造缺失默认值。参数值必须是字符串，结构体／数组按声明编码为 JSON 字符串。编译生成 357 和 657；解码保留原说明行，参数改动会同步说明。无法映射的特殊说明需要完整 `argument_labels` 才能修改参数。

## 查询和读取

先读工程 AGENTS.md，确认项目和目标，不凭名称猜测 ID。

```sh
python3 "<skill>/scripts/events.py" --project "<project>" list --kind common --limit 20
python3 "<skill>/scripts/events.py" --project "<project>" list --kind map --map-id 1
python3 "<skill>/scripts/events.py" --project "<project>" find --text "要查找的文字"
python3 "<skill>/scripts/events.py" --project "<project>" find --calls 100
python3 "<skill>/scripts/events.py" --project "<project>" scan
python3 "<skill>/scripts/events.py" --project "<project>" inspect --target '{"kind":"common","id":167}'
```

地图页目标格式为 `{"kind":"map","map_id":1,"event_id":3,"page_index":0}`；页下标 0 对应编辑器第 1 页，其他 ID 从 1 开始。list 每个地图事件页返回一条摘要；inspect 返回完整 commands、节点范围及指纹。

## 地图事件与事件页

按地图定位事件，再 inspect 查看完整页设置。map_events 的 list 每个事件一条，包含名称、备注、坐标和全部页摘要；search 每个匹配事件页一条，含匹配位置，多个过滤条件按 AND 组合。

```sh
python3 "<skill>/scripts/map_events.py" --project "<project>" list --map-id 1
python3 "<skill>/scripts/map_events.py" --project "<project>" search --name "门卫"
python3 "<skill>/scripts/map_events.py" --project "<project>" search --switch 1
python3 "<skill>/scripts/map_events.py" --project "<project>" search --variable 10
python3 "<skill>/scripts/map_events.py" --project "<project>" inspect --map-id 1 --event-id 4
```

搜索覆盖地图页出现条件、公共事件触发开关、已登记的原生指令引用和移动路线开关；不会将普通数值常量当作变量 ID。脚本、插件参数和动态 ID 不能静态穷尽，结果会标明限制。不能用“无匹配”证明某个 ID 可安全删除。

从 event_api 导入 MapDocument、EventPage。`MapDocument(project, map_id).event(id)` 读取事件；`create_event(name,x,y)` 新建，`delete_event(id)` 删除并保留 null 槽位。不存在的地图不能创建；不要手工修改事件 ID。删除不会修复其他指令的事件引用。

- 事件：`name`、`note`、`x`、`y` 可编辑；note 是编辑器顶部备注，不是 Comment 指令。
- 页：`event.page(0)` 取第 1 页；add_page、copy_page、delete_page、move_page、clear_page 管理页面，至少保留一页。clear_page 重置整页；仅清指令则设置 `page.commands = EventList()`。
- 页设置：set_conditions、set_image、set_movement、set_options；priority、trigger 使用可读枚举，详见 docstring。set_conditions 省略字段保持，None 关闭该项。
- 指令：`page.commands` 是 EventList，接入相同增删改接口。

页出现条件必须同时满足；引擎选择满足条件的最高编号页。调整页序、复制或清空页都可能改变生效页。自主移动路线使用原生 moveRoute 数据，不能把事件 EventList 当作路线；自主移动设置仍接收原生 moveRoute；事件中的 SetMovementRoute 使用 Route 步骤对象，自动同步 205／505。repeat 与 wait 不得同时开启，受阻且不跳过也可能持续等待。图像资源存在性、游戏动态引用和插件行为仍需单独核对。

`document.to_plan()` 导出带整个源地图快照断言的数据库计划，保存到独立 plan.json，再用地图入口应用：

```sh
python3 "<skill>/scripts/map_events.py" --project "<project>" apply --plan "plan.json"
python3 "<skill>/scripts/map_events.py" --project "<project>" apply --plan "plan.json" --write --expect-preview "预览返回的指纹"
```

地图计划与 events.py 的指令计划格式不同，不混用入口。地图计划仍由正式 database.py 后端保持格式、备份、写入和恢复；发生源地图变化时重新读取，不强行套用旧快照。

## 编写与修改

把 scripts 目录加入 Python 搜索路径，从 event_api 导入对象。新建使用 EventList；修改已有事件时，把 inspect 的 commands 传给 `EventList.from_commands()`，保留其他指令。

```python
import json
import sys
from pathlib import Path

sys.path.insert(0, "<skill>/scripts")
from event_api import EventList, Comment

# inspected.json 是正式 inspect 命令输出，不是手动复制的事件片段。
snapshot = json.loads(Path("inspected.json").read_text(encoding="utf-8"))
event = EventList.from_commands(snapshot["commands"])
event.append(Comment("新增注释"))
event.compile()
plan = event.to_plan(snapshot["target"])
Path("plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
```

`find(Type)` 默认递归，返回原对象；可修改属性，或使用 append、extend、insert_before、insert_after、replace、remove。If.then、If.otherwise 和 Loop.body 同样使用 EventList；删除控制块会删除其内部指令。

读取对象的 `to_plan(target)` 自动绑定原列表指纹，生成 replace_all 计划；后端局部序列化，仅改变化的 JSON 区段。新建对象的 to_plan 默认整段替换：只追加时明确 `op="append"` 并传入 inspect 的 `expect_list_sha256`。局部 insert_before、insert_after、replace 使用 inspect 的原始 index 和列表指纹，不使用对象列表下标。一份计划对同一事件列表只允许一个 edit。

未知指令或未支持的参数分型保留为 OpaqueCommand，不直接修改其内部 raw 数据。确需编辑时，先扩展正式对象、编译和解码实现并补行为测试。循环必须有可执行到的 BreakLoop；独立开关、人物和暂时消除事件依赖地图事件上下文。Script/ScriptValue 仅保存字符串，工具不会执行或验证 JavaScript 运行行为。

## 预览、写入和核对

```sh
python3 "<skill>/scripts/events.py" --project "<project>" apply --plan "plan.json"
python3 "<skill>/scripts/events.py" --project "<project>" apply --plan "plan.json" --write --expect-preview "预览返回的指纹"
```

检查预览的 target、before、after 和涉及文件；用户已授权的修改正常执行，无需增加常规确认。发生源文件或计划指纹冲突时重新读取并核对修改意图，不只替换指纹重试。引擎核心方法与兼容配置不匹配时停止语义写入，核对工程实际源码后再适配，不能只改指纹绕过。

写入后再次 inspect，核对目标及未修改内容，记录 transaction 备份路径，按工程约定更新变更记录。恢复使用数据库 skill 的 restore 命令，不手动覆盖文件。数据库事务是逐文件替换，不是跨文件原子事务；recovery_required 时先检查日志。

当前支持公共事件指令及现有地图内的事件、事件页管理，不包含战斗事件列表或新建地图。静态结构检查不代替编辑器显示或 Playtest；报告实际执行过的验证及未验证项。

开发或更名后必须同步更新[指令实现状态](references/command-status.md)。在仓库根目录运行 `python3 -m unittest discover -s tests -v`；工程集成测试通过环境变量启用，并只读原工程、在副本写入。


## 公共事件条目与设置

列出、搜索、创建或删除公共事件条目使用数据库技能 `Database.common_events`。目标不存在时先创建并提交，取得 ID 后再读取、编写指令。仅删除指令仍使用 EventList；删除整条记录交给数据库技能。

事件名称、触发方式和触发开关通过本技能 `common_event_settings_plan(project, id, name=None, trigger=None, switch_id=None)` 修改。trigger 使用 none／autorun／parallel，省略字段保持原值；返回的是数据库计划，使用 `database.py apply` 预览和提交，不传给 events.py apply。该计划绑定原记录，保留所有指令及扩展字段，检查有效触发开关。设置提交后再重新读取指令快照继续编写。
