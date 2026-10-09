# RPG Maker Skills

用于 RPG Maker 工程操作的可独立分发 skills。先实现可验证的文件操作脚本，再由 skill 指导 agent 调用；目标文件修改必须经过脚本。

## 第一个 skill：rpgmaker-plugins

- [SKILL.md](skills/rpgmaker-plugins/SKILL.md)：触发条件与 agent 工作流。
- [脚本需求和接口](skills/rpgmaker-plugins/references/script-contract.md)：支持范围、JSON 计划、写入保证及失败边界。
- [plugins_js.py](skills/rpgmaker-plugins/scripts/plugins_js.py)：Python 3.10+ 标准库实现。
- [行为测试](tests/test_plugins_js.py)：解析、修改、预览、备份、恢复及失败不落盘。

支持 RPG Maker MV/MZ 编辑器式 `js/plugins.js`：读取、校验、增删注册、启停、描述和参数更新、顺序调整、恢复。不会执行 JavaScript。默认只预览，显式写入要求当前文件 SHA-256，并先创建备份。

```sh
python3 skills/rpgmaker-plugins/scripts/plugins_js.py --file "/path/to/project/js/plugins.js" inspect --summary
python3 -m unittest discover -s tests -v
```

可选：使用真实项目做临时副本集成测试，原工程只读；可用 Node.js 时额外做语法检查：

```sh
RPGMAKER_TEST_PROJECT="/path/to/project" python3 -m unittest discover -s tests -v
```

每个 skill 目录完整包含脚本和参考资料，分发时保留目录结构。本仓库的 [AGENTS.md](AGENTS.md) 声明脚本写入约束；在其他工程使用时需让 agent 加载该 skill 或加入对应项目约定。这是 agent 工作流约束，并非文件系统级禁止直接编辑。

首版用 Project1 的 MZ 配置进行只读分析及副本验证，记录见[验证说明](skills/rpgmaker-plugins/references/project-validation.md)。未运行游戏 Playtest，MV 真实工程尚未验证。

Veloria 的复杂嵌套参数测试见[验证记录](skills/rpgmaker-plugins/references/veloria-validation.md)：57 个插件、604 个参数，副本上测试全部 58 个多层参数及 1 个普通参数，最深 6 次 JSON 解码。可用 `python3 tests/probe_nested_project.py /path/to/js/plugins.js` 复现；正式脚本仍采用完整参数字符串输入，深层字段的解码与重新编码由调用方完成。

## 第二个 skill：rpgmaker-database

任何工程数据库修改均触发，覆盖标准数据库、系统、地图、事件指令与自定义 JSON，不按字段名设白名单。普通对象、数组以及多层 JSON 字符串均可通过显式路径直接读写。

- [SKILL.md](skills/rpgmaker-database/SKILL.md)：触发条件与 agent 工作流。
- [脚本接口](skills/rpgmaker-database/references/script-contract.md)：任意字段路径、操作计划、多文件备份与恢复。
- [database.py](skills/rpgmaker-database/scripts/database.py)：Python 3.10+ 标准库实现。
- [行为测试](tests/test_database.py)与[验证记录](skills/rpgmaker-database/references/validation.md)。

```sh
python3 skills/rpgmaker-database/scripts/database.py --root "/path/to/project/data" inspect --file "Actors.json" --path '[3,"name"]'
python3 skills/rpgmaker-database/scripts/database.py --root "/path/to/project/data" apply --plan "/path/to/plan.json"
```

支持替换、新增字段、删除/清空、数组插入与删除、条件断言；默认预览，正式写入必须传回绑定源文件和计划的预览指纹。备份、逐文件原子替换、失败恢复均由脚本处理。多文件写入不具备跨文件原子性，通用字段操作也不自动修复游戏引用或事件结构。仅操作现有 JSON 文件，原工程测试采用只读加临时副本。

## 第三个 skill：rpgmaker-events

- [SKILL.md](skills/rpgmaker-events/SKILL.md)：公共事件和地图事件指令的查询、对象编写、解码及脚本写入工作流。
- [指令实现状态](skills/rpgmaker-events/references/command-status.md)：编译、解码和参数分型的支持范围。
- [统一对象入口](skills/rpgmaker-events/scripts/event_api.py)：用源码 docstring 查询参数；[入门示例](skills/rpgmaker-events/examples/common165.py)。

事件 skill 依赖相邻的 rpgmaker-database，分发时必须同时保留两个目录。工程修改通过 events.py 调用数据库后端，默认预览，显式写入须使用预览指纹。

## 插件统一入口：rpgmaker-plugin

[技能说明](skills/rpgmaker-plugin/SKILL.md)。当前支持插件列表、安装／注册／启用状态、当前参数和命令用法查询，默认简短文本；复用现有清单编辑和声明解析脚本。插件编写流程后续完善。
