# 仓库约定

本仓库存放可独立分发的 RPG Maker skills，每个 skill 放在 `skills/<name>/`。

- 当任务涉及修改 RPG Maker 项目的 `plugins.js` 时，先阅读 `skills/rpgmaker-plugins/SKILL.md`，并且只调用该 skill 的 `scripts/plugins_js.py` 修改目标文件。不得使用直接编辑、补丁、替换文本或临时编写的脚本绕过它，包括回滚。
- 脚本能力不足时，先扩展正式脚本、补充行为测试，再用脚本处理目标文件。测试夹具不受目标文件编辑约束。
- 新增 skill 时先明确脚本输入、输出、失败边界，再编写 skill 工作流。只依赖实际随 skill 分发的资源。
- 验证命令：`python3 -m unittest discover -s tests -v`。
