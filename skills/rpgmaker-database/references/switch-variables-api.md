# 开关与变量名称

`db.switches`、`db.variables` 管理 System.json 中的编号与名称，不设置运行时值。

```python
print(db.switches.list())
print(db.variables.list(search='钟', offset=0, limit=20))
print(db.switches.find('门'))           # [(ID, 名称), ...]
print(db.variables.get(201))
db.switches.set(801, '钟一已损坏')      # 已有编号改名
db.variables.set(201, '插入发条的钟')
db.variables.clear(201)               # 仅清空名称
preview = db.preview()
print(preview)
db.commit(preview)
```

两组均支持 list/find/get/set/clear。list 默认 50 条，包含空名称；find 按名称子串搜索，忽略大小写，保留重名和实际编号。get/set/clear 只接受现有的正整数 ID，0 为保留位。由 agent 根据工程命名分区和已有用途选择编号，再调用 set；不自动追加或分配编号。

空名称不代表未使用；clear 不删除引用，也不清除存档中的值。没有删除或压缩编号操作。引用查找使用事件技能的 `map_events.py search --switch ID` 或 `--variable ID`，动态脚本及插件引用不能穷尽。

需要控制 ON/OFF 或给变量赋值时，交给事件技能的 SetSwitch、ChangeVariable；先提交名称修改，再由事件技能读取并编写指令。
