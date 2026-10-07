# Project1 验证记录

验证日期：2026-10-07。用户授权读取 `/Users/moiyri/Game/RPGMaker/Projects/Project1` 作为真实格式依据。工程只读，修改及恢复全部在系统临时目录的副本中完成；不复制工程配置或插件代码到本仓库。

## 观察

- `game.rmmzproject` 标识 `RPGMZ 1.10.0`。
- `js/plugins.js` 为 49,522 字节，13 个条目，6 个启用、7 个禁用。
- 源文件 SHA-256：`84e44989dc81747b2d32354f490ff123782dba6a4fad73abfbafe9c51406a0d9`。
- 结构为两行注释、`var $plugins =`、严格 JSON 数组及分号；每个插件独占一行。
- 名称包含 `visumz/`、`grace/` 子目录，选择器必须保留完整名称。
- 参数包含普通字符串、JSON 结构体、JSON 字符串数组、多层转义与脚本文本。修改单一字段不能重新解释其他参数。
- 项目 `js/rmmz_managers.js` 的 `PluginManager.setup` 以提取的文件名管理已加载插件；参数表以小写文件名索引。不同目录同 basename 也需检查运行时冲突。

## 结果与复现

```sh
RPGMAKER_TEST_PROJECT="/Users/moiyri/Game/RPGMaker/Projects/Project1" python3 -m unittest discover -s tests -v
```

18 项测试通过（17 项合成夹具测试、1 项真实项目副本集成测试）。集成测试读取源文件后，在临时副本中改变一个插件的启停状态及一个参数，逐项核对其余条目、字段、嵌套参数字符串均保持一致；使用 Node.js `--check` 验证修改后的 JavaScript 语法，随后通过脚本恢复备份，确认恢复后的字节与源文件一致。最后再次比较真实工程原字节，确认原工程未被修改。

测试环境：Python 3.14.4、Node.js v22.16.0。无环境变量时只执行合成测试，真实工程测试标记为跳过。未运行游戏或修改 Project1 的变更记录；MV 真实工程与游戏行为尚未验证。

Skill 元数据校验：官方 `quick_validate.py` 因本机缺少 PyYAML 未能运行；使用 Ruby `YAML.safe_load` 校验 frontmatter 和 `agents/openai.yaml`，并检查命名、字段、描述长度、未完成占位符及默认提示词引用，均通过。脚本本身不依赖 PyYAML。
