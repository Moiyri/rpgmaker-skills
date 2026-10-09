# Types（类型）

对应编辑器 Types 页面，实际存储于 System.json。

| 编辑器栏目 | Python 入口 |
|---|---|
| Elements | `db.types.elements` |
| Skill Types | `db.types.skill_types` |
| Weapon Types | `db.types.weapon_types` |
| Armor Types | `db.types.armor_types` |
| Equipment Types | `db.types.equipment_types` |

```python
print(db.types.elements.list())
print(db.types.elements.find('Fire'))  # 返回 (ID, 名称) 列表
name = db.types.elements.get(2)
db.types.elements.set(2, '火')
new_id = db.types.elements.add('星')
db.types.elements.clear(new_id)       # 清空名称，保留编号
preview = db.preview()
print(preview)
db.commit(preview)
```

五个列表使用相同方法。ID 从 1 开始，0 为保留位；add 追加至末尾，不自动寻找空名称槽位。clear 仅清空名称，不会禁用类型或移除引用；没有删除和重排接口。编辑器 Change Maximum 的缩减暂未封装。

list 返回简短文本，支持 search、offset、limit（默认 50）；包含空名称、重复名称和未提交修改。find 忽略大小写，保留实际编号。本地化名称原样返回，不自动解析。

提交保留 System.json 的其他字段及原有格式，预览后内容变化拒绝提交。类型改名会影响所有引用此编号的显示；不自动修改对应特性、装备或技能。
