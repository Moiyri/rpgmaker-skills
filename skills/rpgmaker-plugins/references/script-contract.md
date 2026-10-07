# plugins.js 脚本需求与接口（v1）

## 目标与边界

用一个 Python 3.10+、仅标准库的命令行入口修改 RPG Maker MV/MZ 的插件清单。
官方依据：[MV Plugin Specifications](https://rpgmakerofficial.com/product/MV_Help/page/01_11_03.html) 明确 `js/plugins.js` 由编辑器写入、使用 UTF-8、参数按字符串处理；[MZ Plugin Manager](https://rpgmakerofficial.com/product/MZ_help-en/01_05.html) 提供启停与参数管理。

本实现支持常见编辑器产物：可选 BOM、前置注释、`var $plugins =`、严格 JSON 数组、可选分号及尾部注释。它不是通用 JavaScript 解析器：不支持表达式、单引号对象、数组内部注释、尾随逗号或额外可执行语句，遇到这些内容拒绝修改，绝不 eval/执行文件。自动测试使用合成夹具，并可通过 `RPGMAKER_TEST_PROJECT` 对真实工程做只读及临时副本测试；见 [Project1 验证记录](project-validation.md)。

首版不负责插件源码下载、安装、依赖推断、参数元数据默认值提取或运行兼容性验证。启用前应由 agent 阅读插件说明、检查 `js/plugins/<name>.js` 存在及加载顺序。空名称占位项和重复名称原样保留，但操作必须选中唯一的非空名称。新增条目不能与现有名称发生大小写不敏感的冲突。

## 输入与输出

```text
python3 <skill>/scripts/plugins_js.py --file <project>/js/plugins.js inspect
python3 <skill>/scripts/plugins_js.py --file <project>/js/plugins.js validate
python3 <skill>/scripts/plugins_js.py --file <project>/js/plugins.js apply --plan <plan.json>
python3 <skill>/scripts/plugins_js.py --file <project>/js/plugins.js apply --plan <plan.json> --write --expect-sha256 <sha256>
python3 <skill>/scripts/plugins_js.py --file <project>/js/plugins.js restore --backup <backup.js>
python3 <skill>/scripts/plugins_js.py --file <project>/js/plugins.js restore --backup <backup.js> --write --expect-sha256 <sha256>
```

必须显式指定现存的 `plugins.js`，不搜索或猜测项目，不创建缺失文件，不接受目标文件为符号链接。`inspect` 输出全部条目与源文件 SHA-256；加 `--summary` 仅输出名称、启停、参数数量，加 `--name "子目录/名称"` 选择唯一条目。`validate` 校验语法范围和字段类型。所有成功结果为 stdout JSON；操作错误为 stderr JSON、退出码 1；命令行用法错误由 argparse 返回退出码 2。

`apply`/`restore` 默认只输出预览，不创建备份或锁。返回 `changed`、`written`、`sha256`、`after_sha256` 和 unified `diff`（JSON 字符串）。显式 `--write` 必须同时传入预览/读取时的 `sha256`。预览后保持计划文件不变。指纹只绑定源文件，不绑定计划文件。

## 操作计划

UTF-8 JSON，顶层仅允许 `version: 1` 与非空 `operations` 数组。操作按数组顺序在内存执行，任何一步失败都不写入。

```json
{
  "version": 1,
  "operations": [
    {"op": "update", "name": "Example", "status": true,
     "parameters": {"Speed": "4", "Enabled": "true", "Text": "中文"}},
    {"op": "move", "name": "Example", "after": "Base"}
  ]
}
```

| 操作 | 必需字段 | 可选字段及语义 |
| --- | --- | --- |
| `add` | `plugin`：完整插件对象 | `before` 或 `after`：唯一的现有插件名称；省略则追加 |
| `update` | `name`；至少一个修改字段 | `status` 布尔值、`description` 字符串、`parameters` 合并键值、`unset_parameters` 删除键名数组 |
| `remove` | `name` | 仅删除注册条目，不删除插件源码 |
| `move` | `name`，且 `before`/`after` 二选一 | 相对于移除自身后的清单定位，不接受以自身为锚点 |

完整插件对象示例：

```json
{"name":"Example","status":false,"description":"示例插件","parameters":{"Count":"10"}}
```

`name` 不包含 `.js` 后缀，必须使用项目中的实际名称，不自动归一化或重命名。保留子目录前缀（如 `grace/Grace_Core`），匹配区分大小写。部分 MZ 运行时按 basename 去重、按小写 basename 存储参数，因此不同目录的同名插件也可能冲突；脚本不推断运行时冲突，新增前由调用方检查。`status` 必须是真正的 JSON boolean；所有参数值必须是字符串，拒绝数字、布尔值、对象、数组及 null，避免隐式序列化改变插件语义。需要 JSON 参数时，由调用方按插件说明生成字符串；例如参数对象 `{"Items":"[\"a\",\"b\"]"}`。结构体数组可能要求每个元素也编码为 JSON 字符串，脚本不猜测层数。

`parameters` 只合并指定键，其他键保持不变；`unset_parameters` 中不存在的键会报错，同一键不能同时设置与删除。操作中的未知字段、JSON 重复键、非标准 NaN/Infinity 均拒绝。插件对象里的扩展字段保留。

## 写入与恢复保证

- 仅替换数组区段，保留前后注释、BOM、外围空白；新数组采用原文件的 CRLF 或 LF 风格，一条插件一行。数组内部原格式不保证保留。
- 语义无变化时原字节不动、不创建备份；保留未知字段、参数字符串、未指定的条目与相对顺序。
- 写入前完整解析生成结果；对原文件做指纹比较。同目录排他锁防止本脚本的并发实例交叉写入，写入前再次比较原字节。
- 每次实际写入先在目标旁的 `.plugins-js-backups/` 创建唯一的原字节备份，然后在同目录写入临时文件、flush/fsync、保留 Unix 权限位，并 `os.replace` 原子替换。备份失败不替换目标；输出备份路径。失败时可能留下有效备份。
- 恢复也使用同一备份/写入流程，并校验备份格式；允许恢复损坏的当前目标，先运行恢复预览获取当前指纹。恢复覆盖的是整份文件，需确认其间的修改是否应该一起撤销。
- 不自动清理备份。进程强制退出可能留下锁或临时文件，确认没有脚本进程工作后再清理。锁不会约束 RPG Maker 编辑器；最后一次检查与替换之间仍存在外部写入窗口。操作前保存编辑器状态并关闭插件管理窗口，修改后重新打开项目/窗口验证，避免编辑器旧状态覆盖。原子替换不承诺断电耐久性或保留扩展属性/ACL。

## 验收

仓库根目录运行 `python3 -m unittest discover -s tests -v`。覆盖解析边界、拒绝可执行内容、字符串参数、整批失败不落盘、预览无副作用、备份恢复、指纹冲突、锁、BOM/CRLF 和未知字段保留。自动测试不能代替真实 MV/MZ 项目的启动与插件行为验证。
