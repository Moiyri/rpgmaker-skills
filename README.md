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
