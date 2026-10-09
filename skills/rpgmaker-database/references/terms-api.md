# Terms（用语）

`db.terms.basic` 基本状态、`params` 能力参数、`commands` 指令、`messages` 消息。四组均支持 list/find/get/set/clear。

```python
print(db.terms.commands.list())
print(db.terms.messages.list(search='save'))
db.terms.basic.set(0, '等级')
db.terms.params.set(0, '最大生命')
db.terms.commands.set(18, '开始游戏')
db.terms.messages.set('saveMessage', '请选择保存位置。')
db.terms.messages.set('levelUp', '%1 升至 %2 %3！')
preview = db.preview()
print(preview)
db.commit(preview)
```

基本状态、能力参数和指令使用原始数组下标（从 0 开始），先 list 查询含义。消息使用原始字符串键；插件新增的已有字符串键也可编辑，不自动新增键。

- `list(search='', offset=0, limit=60)` 返回编号／键、含义及当前文本。消息以引擎键标识用途。
- `find(text)` 按键、栏目说明和文本搜索，返回 `(键, 文本)` 列表。
- `get(key)` 返回当前文本；指令保留位返回 None。
- `set(key, text)` 修改文本；`clear(key)` 清空为字符串，不移除槽位或键。null 保留位不允许修改。

消息中的 `%1`、`%2`、`%3` 为引擎动态替换符，按原消息用途保留。工具不强制占位符相同，也不解析 `${...}` 本地化标记或执行转义内容。修改占位符文本可能绕过工程本地化，应按需求选择。

Terms、Types、System 共享 System.json 快照，可一次提交，保留其他字段及格式。货币名称位于 `db.system.currency_unit`。静态回读验证不代表实际界面已检查。
