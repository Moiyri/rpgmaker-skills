# 任意字段数据库编辑接口 v1

## 范围

Python 3.10+，仅标准库。支持 UTF-8 JSON 数据库中的任意字段：对象、数组、数字、字符串、布尔值、null 和字段内多层 JSON 字符串。不依赖 RPG Maker 字段白名单，MV/MZ 标准数据库、地图、事件与自定义 JSON 使用同一接口。

`--root` 显式指定现存目录，通常是 `<project>/data`。`--file` 或计划中的 `file` 使用相对于根目录的 POSIX 路径。支持根目录内子目录，拒绝 `..`、绝对路径、符号链接路径、事务保留目录及非 JSON 文件。现有文件才可操作；新增 create_file/delete_file 仅支持 MapNNN.json 文件生命周期；其他文件创建删除及非 JSON/二进制数据库不属于此版接口。新增记录或字段可以在现有文件内完成。

## 读取

```sh
python3 "<skill>/scripts/database.py" --root "<project>/data" inspect --file "Actors.json" --summary
python3 "<skill>/scripts/database.py" --root "<project>/data" inspect --file "Actors.json" --path '[3,"traits",0,"value"]'
python3 "<skill>/scripts/database.py" --root "<project>/data" inspect --file "System.json" --path '["terms"]' --children
python3 "<skill>/scripts/database.py" --root "<project>/data" inspect --file "custom.json" --path-file "<path.json>"
python3 "<skill>/scripts/database.py" --root "<project>/data" validate --file "Map001.json"
```

`inspect` 默认路径为 `[]`（整个文件），返回原文件 SHA-256 和完整 `value`。`--summary` 仅返回类型、大小及值摘要；大型值摘要最多 240 个字符，附完整值的哈希。`--children` 列出直接子字段路径与摘要，不递归解码所有字符串。字符串可解码为 JSON 时，返回 `decoded_path`，由调用方按数据含义决定是否沿该路径读取。`--path-file` 与非默认 `--path` 不能同时使用。

`validate` 只校验严格 JSON 语法，拒绝重复对象键、NaN、Infinity 及超出有限浮点范围的数。不会执行 JavaScript 或判断游戏数据是否具有正确的含义。解析和遍历仍受 Python 内存、递归深度及数字长度限制；超限失败，不宣称无限容量。

## 路径

路径是 JSON 数组，逐项解释：

| 路径项 | 含义 |
| --- | --- |
| `"field"` | 对象的精确键名，允许空字符串、中文、点号、斜杠等字符 |
| `0` | 数组的非负整数下标；不接受负数、布尔值或 `"0"` 代替下标 |
| `{"decode":"json"}` | 将当前字符串按严格 JSON 解码；修改后自动编码回字符串 |
| 整条路径 `[]` | 当前文件的根值 |

例如 `actorConfigs` 是 JSON 编码的数组，其元素又是 JSON 编码对象：

```json
["actorConfigs", {"decode":"json"}, 0, {"decode":"json"}, "name"]
```

如果 `name` 本身是 `"123"`，到此读取结果仍是字符串 `"123"`。再显式添加一个解码步骤才会读取为数字 `123`。没有隐式类型推断；普通文本、脚本文本及数字字符串都可以保持原样。

路径不存在、索引越界、结构类型不符或解码失败，整批操作停止。不存在的中间对象不会自动生成，先用 `put` 或 `set` 显式创建它们。支持同一条路径中的多次解码及解码后根值替换。

## 操作计划

独立 UTF-8 JSON 文件：

```json
{
  "version": 1,
  "operations": [
    {"op":"test", "file":"Actors.json", "path":[3,"id"], "expect":3},
    {"op":"set", "file":"Actors.json", "path":[3,"traits",0,"value"], "expect":1, "value":1.2},
    {"op":"set", "file":"System.json", "path":["switches",10], "value":"任务已完成"}
  ]
}
```

操作按顺序在内存中执行，后面的路径和 `expect` 面向前面操作完成后的状态。所有文件与全部操作先完成校验和序列化，成功后才允许实际写入。

| 操作 | 除 `op/file/path` 外的字段 | 行为 |
| --- | --- | --- |
| `set` | 必需 `value`，可选 `expect` | 替换存在的值，包括根值；可显式改变 JSON 类型 |
| `put` | 必需 `value` | 新增一个不存在的对象字段，拒绝覆盖及数组下标 |
| `remove` | 可选 `expect` | 对象键删除；数组槽设为 null，保留后续下标；不能删除文件根值 |
| `splice` | 必需 `index/delete_count/items`，可选 `expect` | 目标路径必须为数组；替换连续区间，`items` 必须是数组 |
| `test` | 必需 `expect` | 检查当前值，不修改 |

`splice` 的 `index` 范围为 `0..数组长度`，`delete_count` 不得越界；末尾追加使用 `index = 数组长度, delete_count = 0`。它会改变后续下标，不自动调整任何记录 ID 或引用。数据库 ID 表删除通常应使用 `remove` 留空槽；新增记录可 `set` 一个 null 槽，或以 `splice` 追加完整对象。

`expect` 对类型敏感：`true`、`1` 和 `1.0` 不视为相同。脚本不对值做隐式强制转换，也不会根据旧类型禁止用户明确请求的类型变化。未知操作字段会报错，避免拼写错误被忽略。

多层字段修改示例：

```json
{
  "version":1,
  "operations":[
    {
      "op":"set", "file":"custom.json",
      "path":["actorConfigs",{"decode":"json"},0,{"decode":"json"},"outfits",{"decode":"json"},0,{"decode":"json"},"name"],
      "expect":"旧名称", "value":"新名称"
    }
  ]
}
```

事件指令同样可直接读写，例如 `[64,"list",10,"parameters",3,"filterParameters",{"decode":"json"},2]`，不需要提前注册这个字段。事件页、控制分支、脚本参数和图块数组的结构正确性由调用方结合项目与引擎核对。

## 预览、写入与恢复

```sh
python3 "<skill>/scripts/database.py" --root "<project>/data" apply --plan "<plan.json>"
python3 "<skill>/scripts/database.py" --root "<project>/data" apply --plan "<plan.json>" --write --expect-preview "<preview_sha256>"
python3 "<skill>/scripts/database.py" --root "<project>/data" restore --transaction "<transaction.json>"
python3 "<skill>/scripts/database.py" --root "<project>/data" restore --transaction "<transaction.json>" --write --expect-preview "<preview_sha256>"
```

默认预览，没有文件、备份或锁写入。返回：

- `files`：各文件修改前后的 SHA-256 与 `changed`。
- `changes`：每步操作的路径、前后值摘要（仅 apply）。
- `preview_sha256`：绑定根目录、操作计划及全部源文件/目标字节指纹；写入必须传回该值。
- `written`：是否真正写入；实际写入返回 `transaction` 清单路径。

输入计划不变且源文件不变时预览指纹稳定。计划、源文件或根目录变化都会使旧预览失效。无变化时原字节保持不动，不创建事务、备份或锁。`set` 重复设置相同值可无变化；`put`、`splice`、带旧值 `expect` 的计划不承诺可重复执行。

实际写入获得根目录 `.rpgmaker-db.lock` 排他锁，在 `.rpgmaker-db-backups/txn-*/` 备份每个有变化的文件，并记录 `transaction.json`。先准备全部临时文件、flush/fsync，再逐文件 `os.replace`；写前再次核对源字节。保留 Unix 权限位、BOM 和 LF/CRLF 风格，无变化时保留全部字节；有变化时可规范化该文件 JSON 排版。解码路径上被修改的 JSON 字符串会重新排版，未修改的同级字符串值保持不变。数字的文本表示可能被规范化。

多文件**不是跨文件原子事务**。捕获到写入失败时，脚本尝试恢复已经替换且没有再次被外部编辑的文件，并记录 `rolled_back`。存在外部新修改或恢复失败时，保留原备份，报告 `recovery_required` 及事务路径，不覆盖检测到的新修改。成功时状态为 `committed`。

恢复校验事务根目录、备份路径及备份 SHA-256，然后以同样流程恢复事务内整份文件；恢复前状态也创建新事务。允许当前文件 JSON 损坏时恢复，但文件必须存在。`restore` 不会只恢复原来改过的字段，因此会覆盖该文件后来发生的其他修改。

锁只协调本脚本，不能锁住 RPG Maker 编辑器。检查与替换间仍存在外部写入窗口；进程强制终止/断电可能留下 `prepared` 日志、锁、临时文件或部分替换。先核对文件和日志，在确认无脚本运行后处理残留锁，再通过 `restore` 预览恢复。日志不等同于断电安全保证。备份不自动清理，扩展属性/ACL 不承诺保留。

成功输出 stdout JSON，操作错误输出 stderr JSON、退出码 1；参数用法错误由 argparse 输出并返回 2。错误不等于已完成修改；若含事务路径，应核对恢复状态。

## 验证

```sh
python3 -m unittest discover -s tests -v
RPGMAKER_TEST_PROJECT="/path/to/project" python3 -m unittest discover -s tests -v
```

真实项目测试只读取原文件，在临时副本中修改与恢复。已验证范围见 [验证记录](validation.md)。不包含引用搜索、自动 ID 迁移、引擎语义验证或 Playtest；这些不限制字段读写能力，也不能用 JSON 语法通过代替。


## 地图文件生命周期

`{"op":"create_file","file":"Map003.json","text":"完整 JSON 文本"}` 要求路径不存在；`{"op":"delete_file","file":"Map003.json"}` 删除已有地图。与 MapInfos 修改放入同一计划。仅允许根目录 MapNNN.json 文件名；创建文本须合法 JSON。调用方使用地图 API 生成默认值并检查引用，不手工拼装地图数据。

预览中不存在的前／后文件哈希为 null；事务及 restore 支持创建和删除。创建以原子禁止覆盖方式发布。失败回滚保留外部并发修改，不保证多文件操作系统级原子性。撤销创建仅在新文件内容仍等于提交结果时允许；恢复删除要求路径仍未占用。
