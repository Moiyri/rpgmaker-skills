---
name: rpgmaker-plugins
description: 查询 RPG Maker 工程插件列表、安装注册及启用状态、当前参数与插件命令用法，并通过正式脚本修改 js/plugins.js 的注册、启停、加载顺序和参数。事件依赖插件或需要管理插件配置时使用，以及插件源码的创建、修改和删除。
---

# RPG Maker 插件

查询使用 `scripts/plugin.py`，清单写入和恢复使用 `scripts/plugins_js.py`。Python 3.10+；`<skill>` 为本目录，`<project>` 为工程根目录。

查询返回简短文本，不执行 JavaScript；只解析编辑器式 plugins.js。列表、状态和当前参数查询使用本技能内置解析器；命令帮助复用相邻 `rpgmaker-events/scripts/event_core/plugin_help.py`，需要该功能时同时分发事件技能及其数据库依赖。缺少依赖时明确报错，不猜测命令参数。

## 查询

`<skill>` 为本目录，`<project>` 为工程根目录。

```sh
python3 "<skill>/scripts/plugin.py" --project "<project>" list
python3 "<skill>/scripts/plugin.py" --project "<project>" list --search Message --enabled
python3 "<skill>/scripts/plugin.py" --project "<project>" check --plugin Ve_1_Message
python3 "<skill>/scripts/plugin.py" --project "<project>" parameters --plugin Ve_1_Message
python3 "<skill>/scripts/plugin.py" --project "<project>" parameters --plugin Ve_1_Message --parameter defaultLanguage
python3 "<skill>/scripts/plugin.py" --project "<project>" help --plugin Ve_1_Message
python3 "<skill>/scripts/plugin.py" --project "<project>" help --plugin Ve_1_Message --command ShowDialogue
```

- list：按清单加载顺序列出注册项，再列未注册的 .js 文件；不把文件存在等同于启用。
- check：区分未安装、未注册、已禁用、文件缺失和已启用。启用状态只是清单配置，不证明运行时加载成功。
- parameters：工程当前配置值；长值概要省略，指定参数取得完整值，保留多层编码字符串。
- help：插件声明的命令及用法。`--section parameters` 查看配置参数声明及默认值，`--struct 名称` 查看结构体，`--section help` 查看完整帮助；`--language` 选择语言。当前值与声明默认值不是一回事。

Python 方法：`check_plugin(project, plugin)`、`list_plugins(project)`、`plugin_parameters(project, plugin, parameter=None)`、`plugin_help(project, plugin, command=None, section='commands', struct=None)`，返回文本。

## 事件开发联动

编写依赖插件的事件前先 check，再 help 查询命令和参数；同一工程同一插件本轮检查一次即可，配置变化后重新检查。缺失、未注册或禁用时报告，不因检查而擅自安装或启用。原生事件指令无需检查插件。

## 参数修改：先查询声明，再按路径设置

修改插件参数时必须先调用 `Plugins.parameter_help(name)`（或 CLI `parameter-help`），从插件的 @param/@type/struct 声明获得参数用途、类型、可选值、限制和路径。不凭字段名猜参数，不要求 agent 阅读源码或手动 JSON 编解码。

输出为简短文本；根查询列参数，传入路径只展开一层。结构体和数组不输出整串配置，下标从 0 开始。直接复制输出的路径调用 `set_parameter`：

```python
plugins = Plugins(project)
print(plugins.parameter_help("VisuMZ_0_CoreEngine"))
print(plugins.parameter_help("VisuMZ_0_CoreEngine", ["CustomParam:arraystruct", 0]))
plugins.set_parameter("VisuMZ_0_CoreEngine",
                      ["CustomParam:arraystruct", 0, "ParamName:str"], "力量")
preview = plugins.preview()
print(preview["diff"])
plugins.commit(preview)
```

普通参数也用该方法：`set_parameter(name, ["Enabled"], True)`。数字传 Python 数值、布尔传 bool、数组传 list、结构体传 dict；select 使用声明的 value。脚本按声明解码并恢复结构体、数组及 note 编码，支持连续多次修改，保留未修改字段和未知内容。结构体 dict 合并，数组 list 替换整数组；改一个元素优先指定下标路径。

缺失/重复声明、编码不符、字段或下标不存在、参数类型/范围不符时停止，不猜编码层数。未配置的容器不会默默采用默认值创建，必须明确设置；普通未配置字段可按声明设置。字符串即使看似 JSON，也不擅自按结构体解析。动态参数或非标准编码需要先扩展正式解析器及测试，不能让 agent 手工重写整串绕过。

```sh
python3 "<skill>/scripts/plugin.py" --project "<project>" parameter-help --plugin "VisuMZ_0_CoreEngine"
python3 "<skill>/scripts/plugin.py" --project "<project>" parameter-help --plugin "VisuMZ_0_CoreEngine" --path '["CustomParam:arraystruct",0]'
```

参数声明解析复用随相邻事件技能分发的解析器。源配置或声明在修改期间变化时重新读取，不覆盖其他修改。低层 update(parameters=...) 保留用于已编码数据兼容，不作为 agent 日常参数编辑入口。

## 清单编辑对象接口

使用 `scripts/plugin_api.py` 的 `Plugins(project)`：list/get 读取，add 新增注册，update 修改启停／说明／参数，remove 移除注册，move 调整顺序。先 preview() 检查 diff，再 commit(preview)；源文件或计划改变时拒绝写入。接口内部调用正式 plugins_js.py，无需手写 JSON 计划。参数值必须为字符串。

见[编辑示例](examples/edit_plugins.py)。remove 不删除插件源码；add 要求文件已存在。所有名字使用完整注册路径。

## 插件源码

创建、修改和删除插件源码，以及嵌套参数、重命名和卸载步骤，见[源码工作流](references/source-workflow.md)。源码可正常编辑；plugins.js 的任何变更仍必须走正式脚本。Debug 工程扩展优先使用子插件，不直接修改基础框架。

## 必须通过脚本写入

对目标工程的 `plugins.js` 的所有修改（包括恢复）必须调用本 skill 自带的 `scripts/plugins_js.py`。禁止直接编辑、apply_patch、sed/正则替换、通过临时脚本重写或执行目标 JavaScript。可以正常读取目标、编写 JSON 操作计划、编辑插件源码。

脚本不支持所需操作或拒绝输入时，不要绕过：先检查原因；如确需扩展，修改正式脚本并验证后再调用。不得把运行任意 JavaScript 当作解析手段。

## 工作流

1. 明确目标工程及其 `js/plugins.js`，读取适用的项目约定。将下面 `<skill>` 替换为本 `SKILL.md` 所在目录，路径均正确引用；不依赖当前工作目录或固定的用户路径。
2. 用脚本读取概览，再按需读取目标插件。保留子目录名称（如 `grace/Grace_Core`），不要只使用 basename。

   ```sh
   python3 "<skill>/scripts/plugins_js.py" --file "<project>/js/plugins.js" inspect --summary
   python3 "<skill>/scripts/plugins_js.py" --file "<project>/js/plugins.js" inspect --name "grace/Grace_Core"
   ```

3. 阅读 [脚本接口与操作计划](references/script-contract.md)，在独立 JSON 文件中编写计划。只改用户请求的字段；新增或启用前检查实际插件文件、说明、依赖和加载顺序，不自动启用其他插件。插件参数值必须是字符串，`status` 必须是布尔值。参数修改使用上面的声明查询和 set_parameter 路径接口，脚本负责编码。
4. 运行预览，检查 `diff` 与 `changed`。保留返回的 `sha256`，写入前不要改变计划。

   ```sh
   python3 "<skill>/scripts/plugins_js.py" --file "<project>/js/plugins.js" apply --plan "<plan.json>"
   ```

5. 在用户已授权的修改范围内继续执行，无需额外询问常规写入许可。避免编辑器同时保存插件配置；使用预览返回的源文件指纹执行写入：

   ```sh
   python3 "<skill>/scripts/plugins_js.py" --file "<project>/js/plugins.js" apply --plan "<plan.json>" --write --expect-sha256 "<sha256>"
   ```

   指纹冲突时重新读取、核对修改意图并预览，不能只换指纹强行重试。其他错误按接口说明处理；失败时不要宣称已完成。
6. 再用 `inspect`/`validate` 核对结果，记录脚本返回的备份路径，按项目要求补充变更记录。报告变更与验证边界：文件校验通过不代表插件依赖、游戏启动和运行行为已验证。任务涉及游戏行为时执行适用的 Playtest，无法执行则明确说明。

## 恢复

使用 `restore --backup "<backup.js>"` 预览；确认恢复范围后，以预览返回的当前文件指纹加 `--write --expect-sha256 "<sha256>"` 执行。不要直接复制备份覆盖目标。恢复整个文件会撤销备份之后的其他修改。

## 关键边界

- 只接受编辑器式 `var $plugins = <JSON array>`，不执行表达式或插件代码；格式不支持时停止并说明原因。
- `update.parameters` 合并指定键；删除参数必须用 `unset_parameters`。保留未知字段和未指定的参数字符串。
- 按名称唯一匹配，重名或不存在时失败；不擅自选第一个条目。移动使用明确的 `before`/`after`，不按字母自动排序。
- 默认预览、写入前备份、整批验证成功后原子替换。锁只能协调本脚本；编辑器仍可能覆盖外部修改。
