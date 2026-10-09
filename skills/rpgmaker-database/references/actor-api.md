# 角色接口

从 `database_api` 导入 `Database`，使用 `db.actors`。入口与物品一致，修改后 `preview()`、`commit(preview)`；一次提交可同时包含物品和角色。

```python
print(db.actors.list())
print(db.actors.list(include_empty=True, offset=0, limit=50))
for actor in db.actors.find('勇者'):
    print(actor.id, actor.name)
actor = db.actors.get(1)
print(actor.describe())
actor.nickname = '旅行者'
actor.initial_level = 5
actor.class_id = 1
actor.character_name = 'Actor1'
actor.character_index = 0
actor.equip(0, 0)                      # 清空初始装备第一个槽
actor.traits.add('state_resist', id=1) # 状态免疫
print(actor.traits.list())
actor.traits.remove(0)
new_actor = db.actors.create('守卫')   # 追加；id=2 指定空槽
print(db.actors.references(2))
db.actors.clear(2)                    # 清空保留编号
preview = db.preview()
print(preview)
db.commit(preview)
```

| 属性 | 用途 |
|---|---|
| `id` | 只读编号 |
| `name`, `nickname`, `profile`, `note` | 名称、昵称、简介、备注 |
| `class_id` | 职业 ID |
| `initial_level`, `max_level` | 初始、最大等级，1–99，初始不能超过最大 |
| `character_name`, `character_index` | 行走图文件名与索引 0–7 |
| `face_name`, `face_index` | 脸图文件名与索引 0–7 |
| `battler_name` | 侧视战斗图文件名 |
| `equipment` | 初始装备 ID 列表副本；使用 `equip(slot,id)` 修改 |

图片名不含扩展名，空字符串表示无图片。索引和装备槽下标从 0 开始。装备 ID 0 表示无装备；武器／防具类型依槽位、职业及双持特性确定。当前不自动验证素材存在性或装备适用性。

`traits` 提供 `list/get/add/remove/clear`。`get` 返回副本，修改已有特性使用 `actor.set(['traits', 0, 'value'], 1.2)`。`add(kind,id=0,value=1)` 中比率使用 1.0 表示 100%；参数编号、标记和比率须按具体特性含义选择，当前未封装每种特性的独立参数校验。

kind 支持：`element_rate`, `debuff_rate`, `state_rate`, `state_resist`, `parameter_rate`, `extra_parameter`, `special_parameter`, `attack_element`, `attack_state`, `attack_speed`, `attack_times`, `attack_skill`, `skill_type`, `seal_skill_type`, `skill`, `seal_skill`, `weapon_type`, `armor_type`, `lock_equipment`, `seal_equipment`, `slot_type`, `action_plus`, `special_flag`, `collapse_type`, `party_ability`。

创建只使用标准空白槽、null 槽或末尾；清空移除全部设置及插件字段，不删除槽位、不更新引用。未知字段通过 `get/set` 嵌套路径访问，未修改内容保留。职业新增或改动时检查引用。

引用查询覆盖初始队伍、公共／地图／战斗事件中的原生角色指令、角色条件和变量获取角色数据；脚本、插件及动态变量引用不解析，无结果不代表无引用。角色数据库设置主要影响新游戏，不更新已有存档。

## 特性 ID 的查询来源

| 特性 kind | 查询入口 |
|---|---|
| element_rate、attack_element | `db.types.elements.list()` |
| skill_type、seal_skill_type | `db.types.skill_types.list()` |
| weapon_type | `db.types.weapon_types.list()` |
| armor_type | `db.types.armor_types.list()` |
| lock_equipment、seal_equipment | `db.types.equipment_types.list()` |
| debuff_rate、parameter_rate | [固定编号](engine-enums.md) parameters |
| extra_parameter、special_parameter | 固定编号 extra_parameters、special_parameters |
| slot_type、special_flag、collapse_type、party_ability | 固定编号对应表 |
| state_rate、state_resist、attack_state | 正式数据库脚本 inspect States.json |
| skill、seal_skill、attack_skill | 正式数据库脚本 inspect Skills.json |

attack_speed、attack_times、action_plus 不使用 ID，保留默认 0。

```python
print(db.types.skill_types.list())
# 根据实际输出确认 Magic 的编号；假设为 1：
actor.traits.add('skill_type', id=1)
```

Types 列表包含当前会话未提交的修改。固定枚举不是可编辑类型；尚未实现技能、状态等对象列表接口，不假定其存在。
