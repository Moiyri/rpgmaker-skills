---
name: rpgmaker-plugins
description: 通过随附脚本安全编辑 RPG Maker MV/MZ 的 js/plugins.js，适用于增删插件注册、启用或禁用插件、调整加载顺序及修改插件参数。只要任务需要修改该文件就使用此 skill；插件源码本身的修改不属于本 skill。
---

# RPG Maker 插件清单编辑

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

3. 阅读 [脚本接口与操作计划](references/script-contract.md)，在独立 JSON 文件中编写计划。只改用户请求的字段；新增或启用前检查实际插件文件、说明、依赖和加载顺序，不自动启用其他插件。插件参数值必须是字符串，`status` 必须是布尔值。嵌套结构按插件格式逐层 JSON 编解码后作为字符串传入；不要猜测编码层数或改写嵌入的脚本文本。
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
