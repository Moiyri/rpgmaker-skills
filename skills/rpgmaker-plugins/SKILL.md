---
name: rpgmaker-plugins
description: 查询 RPG Maker 工程插件列表、安装注册及启用状态、当前参数与插件命令用法，并通过正式脚本修改 js/plugins.js 的注册、启停、加载顺序和参数。事件依赖插件或需要管理插件配置时使用，以及插件源码的创建、修改和删除。
---

# RPG Maker 插件

统一入口为 `scripts/plugins.py`，同时提供 Python API 和 CLI。Python 3.10+；`<skill>` 为本目录，`<project>` 为工程根目录。

查询返回简短文本，不执行 JavaScript；只解析编辑器式 plugins.js。声明解析、结构帮助和参数编码均随本技能分发，不依赖事件技能。事件技能复用这里的声明解析器，不猜测命令参数。

## 查询与帮助

统一从 `plugins.py` 导入 `Plugins`。help 只查询顶层结构和指定结构体，按“字段 | 用途 | 类型”分列，分组作为标题，过滤装饰项；长选项列表去重并集中列出，保留数值限制，不展开配置实例或长脚本。字段用途沿用插件声明名称，不维护额外翻译表。

```python
from plugins import Plugins
plugins = Plugins(project)
plugin = plugins.get("Liy_Graphics")
print(plugin.parameters.list())      # 全部顶层参数和结构体名称
print(plugin.parameters.list("Map")) # 该结构体全部字段和类型
print(plugin.help())                 # 顶层参数详情
print(plugin.help("Map"))            # Map 结构体的直接字段
print(plugin.help("LayerSprite"))    # LayerSprite 结构体的直接字段
```

```sh
python3 "<skill>/scripts/plugins.py" --project "<project>" list --search Graphics
python3 "<skill>/scripts/plugins.py" --project "<project>" check --plugin Liy_Graphics
python3 "<skill>/scripts/plugins.py" --project "<project>" help --plugin Liy_Graphics
python3 "<skill>/scripts/plugins.py" --project "<project>" help --plugin Liy_Graphics --struct Map
```

`struct<X>` 和 `struct<X>[]` 中的 X 是可查询的结构体名称。嵌套结构不重复展开。`plugin.parameters.help(struct)` 与 `plugin.help(struct)` 相同。

当前配置使用 `plugin.parameters.get(path)` 读取。修改前通过 help 获取相关声明，不猜参数，不手动处理嵌套 JSON。使用 `parameters.set(path, value)` 修改、`append(path, value)` 添加数组项；`item_defaults(path)` 获取数组元素的声明默认值。路径使用字段名和从 0 开始的数组下标，值使用 Python 原生类型。结构体 dict 合并，数组 list 替换整个数组。缺失声明、非法编码、错误类型和越界下标会拒绝操作。

插件命令与配置结构分开：`plugin.commands.list()` 列出命令，`plugin.commands.help(command_id)` 查询命令参数。事件依赖插件时先 check，再查询命令；原生指令无需检查插件。缺失或禁用不代表允许自动安装或启用。

见[新增语言示例](examples/add_message_language.py)。参数编解码和存储由内部 plugin_core 负责；源配置或声明变化时重新读取并预览。

## 清单编辑对象接口

使用 `scripts/plugins.py` 的 `Plugins(project)`：list/get 读取，add 新增注册，update 修改启停／说明／参数，remove 移除注册，move 调整顺序。先 preview() 检查 diff，再 commit(preview)；源文件或计划改变时拒绝写入。底层存储由内部 `plugin_core/storage.py` 负责，无需手写 JSON 计划。普通参数修改使用 parameters.set/append，由脚本处理编码。

见[编辑示例](examples/edit_plugins.py)。remove 不删除插件源码；add 要求文件已存在。所有名字使用完整注册路径。

## 插件源码

创建、修改和删除插件源码，以及嵌套参数、重命名和卸载步骤，见[源码工作流](references/source-workflow.md)。源码可正常编辑；plugins.js 的任何变更仍必须走正式脚本。Debug 工程扩展优先使用子插件，不直接修改基础框架。

## 必须通过脚本写入

对目标工程的 `plugins.js` 的所有修改（包括恢复）必须调用本 skill 自带的 `scripts/plugins.py`。禁止直接编辑、apply_patch、sed/正则替换、通过临时脚本重写或执行目标 JavaScript。可以正常读取目标、编写 JSON 操作计划、编辑插件源码。

脚本不支持所需操作或拒绝输入时，不要绕过：先检查原因；如确需扩展，修改正式脚本并验证后再调用。不得把运行任意 JavaScript 当作解析手段。

## 工作流

1. 明确目标工程及其 `js/plugins.js`，读取适用的项目约定。将下面 `<skill>` 替换为本 `SKILL.md` 所在目录，路径均正确引用；不依赖当前工作目录或固定的用户路径。
2. 用脚本读取概览，再按需读取目标插件。保留子目录名称（如 `grace/Grace_Core`），不要只使用 basename。

   ```sh
   python3 "<skill>/scripts/plugins.py" --file "<project>/js/plugins.js" inspect --summary
   python3 "<skill>/scripts/plugins.py" --file "<project>/js/plugins.js" inspect --name "grace/Grace_Core"
   ```

3. 阅读 [脚本接口与操作计划](references/script-contract.md)，在独立 JSON 文件中编写计划。只改用户请求的字段；新增或启用前检查实际插件文件、说明、依赖和加载顺序，不自动启用其他插件。插件参数值必须是字符串，`status` 必须是布尔值。参数修改使用上面的声明查询和 set_parameter 路径接口，脚本负责编码。
4. 运行预览，检查 `diff` 与 `changed`。保留返回的 `sha256`，写入前不要改变计划。

   ```sh
   python3 "<skill>/scripts/plugins.py" --file "<project>/js/plugins.js" apply --plan "<plan.json>"
   ```

5. 在用户已授权的修改范围内继续执行，无需额外询问常规写入许可。避免编辑器同时保存插件配置；使用预览返回的源文件指纹执行写入：

   ```sh
   python3 "<skill>/scripts/plugins.py" --file "<project>/js/plugins.js" apply --plan "<plan.json>" --write --expect-sha256 "<sha256>"
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
