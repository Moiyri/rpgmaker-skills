# 仓库约定

本仓库存放可独立分发的 RPG Maker skills，每个 skill 放在 `skills/<name>/`。

- 当任务涉及修改 RPG Maker 项目的 `plugins.js` 时，先阅读 `skills/rpgmaker-plugins/SKILL.md`，并且只调用该 skill 的 `scripts/plugins_js.py` 修改目标文件。不得使用直接编辑、补丁、替换文本或临时编写的脚本绕过它，包括回滚。
- 当任务涉及任何 RPG Maker 工程数据库修改时，先阅读 `skills/rpgmaker-database/SKILL.md`，通过该 skill 的 `scripts/database.py` 修改及恢复。覆盖标准数据库、系统配置、地图、事件及明确指定的自定义 JSON 数据库；任意字段和多层编码字段都适用，不直接编辑目标 JSON。`plugins.js` 仍使用插件清单 skill。
- 脚本能力不足时，先扩展正式脚本、补充行为测试，再用脚本处理目标文件。测试夹具不受目标文件编辑约束。
- 新增 skill 时先明确脚本输入、输出、失败边界，再编写 skill 工作流。只依赖实际随 skill 分发的资源。
- 事件指令实现状态统一记录在 [指令实现状态表](skills/rpgmaker-events/references/command-status.md)。每次完成事件指令、条件或操作数的开发、修改、重命名或移除后，必须同步更新对应行的接口名称、编译／解码状态、支持范围与限制，并更新验证记录；未测试的能力不得标记为已实现。仅能原样保留的指令不得标记为支持语义编辑。
- 验证命令：`python3 -m unittest discover -s tests -v`。

- 事件命令对象统一放入 event_core/commands/，内部按引擎分类；地图管理、查询、编解码与指令目录分开。对外统一由 event_api.py 导出。
