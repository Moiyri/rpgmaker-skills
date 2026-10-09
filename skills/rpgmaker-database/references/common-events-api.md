# 公共事件条目

数据库技能仅负责列表、搜索、创建和删除。名称及触发设置的后续修改、所有指令编写由事件技能负责。

```python
print(db.common_events.list())
print(db.common_events.list(include_empty=True, offset=0, limit=50))
for entry in db.common_events.find('钥匙'):
    print(entry.id, entry.name, entry.trigger)
entry = db.common_events.create()  # 默认追加；id=1207 指定空槽
print(entry.id)
preview = db.preview()
print(preview)
db.commit(preview)
# 接下来把工程路径、entry.id 交给事件技能。
```

create 可给初始名称，返回不可修改的摘要（id/name/trigger/switch_id），不暴露指令列表。初始记录触发方式为 none，指令仅有引擎结束标记。目标只允许标准空白记录、null 或末尾；未命名但包含指令的条目不会被当成空白。

`db.common_events.delete(id)` 清空名称、触发设置、所有指令及扩展字段，保留编号，不移动后续记录。不自动修复调用引用，删除前可使用事件技能 `find --calls ID` 检查直接调用，并检查物品／技能效果及插件引用。仅清空指令时使用事件技能，不调用 delete。

条目管理共用 Database.preview/commit，创建提交后再让事件技能读取和编辑，避免旧快照冲突。
