# 物品接口

将 skill 的 `scripts` 加入 Python 导入路径，使用 `database_api`。详细参数可通过 `help(Database)`、`help(Item)`、`help(RecoverHP)` 查看；完整可运行示例见 [items.py](../examples/items.py)。

```python
from database_api import Database, RecoverHP

db = Database('/path/to/project')
print(db.items.list())                     # 默认 50 条，跳过未命名记录
print(db.items.list(include_empty=True, offset=50, limit=50))
for item in db.items.find('药水'):
    print(item.id, item.name)

item = db.items.get(1)                     # 使用实际 ID
print(item.describe())
item.name = '药水'
item.description = '恢复 100 HP。'
item.consumable = True
item.effects.add(RecoverHP(amount=100))    # 追加，不清除已有效果
preview = db.preview()
print(preview)
backup = db.commit(preview)
```

一次会话可修改多个物品；提交后重新打开 `Database`。预览后内容或文件变化会拒绝提交。写入复用 `database.py`，保留格式并生成事务备份；恢复使用该脚本的 `restore`。

## 字段

| 对象属性 | 引擎设置／值 |
|---|---|
| `id` | ID，只读 |
| `name`, `description`, `note` | 名称、说明、备注，字符串 |
| `icon_index`, `price` | 图标编号、价格，非负整数 |
| `item_type` | `regular`, `key_item`, `hidden_a`, `hidden_b` |
| `consumable` | 是否消耗，布尔值 |
| `scope` | 见下方作用范围 |
| `occasion` | `always`, `battle`, `menu`, `never` |
| `speed`, `success_rate`, `repeats`, `tp_gain` | 速度 -2000–2000、成功率 0–100、重复 1–9、TP 0–100 |
| `hit_type` | `certain`, `physical`, `magical` |
| `animation_id` | 动画 ID；0 无，-1 普通攻击 |
| `damage.type` | `none`, `hp_damage`, `mp_damage`, `hp_recover`, `mp_recover`, `hp_drain`, `mp_drain` |
| `damage.element_id` | 属性 ID；0 无，-1 普通攻击 |
| `damage.formula`, `damage.variance`, `damage.critical` | JS 公式字符串、离散度 0–100、允许暴击 |

`scope`：`none`, `one_enemy`, `all_enemies`, `random_1_enemy` 至 `random_4_enemies`, `one_ally`, `all_allies`, `one_dead_ally`, `all_dead_allies`, `user`, `one_ally_any`, `all_allies_any`, `everyone`。最后三种为 MZ 范围，不保证 MV 兼容。

## 使用效果

| 构造方法 | 含义 |
|---|---|
| `RecoverHP(percent=0, amount=0)` | HP 恢复：最大值百分比 + 固定值，可为负数 |
| `RecoverMP(percent=0, amount=0)` | MP 恢复，同上 |
| `GainTP(amount=0)` | 增加 TP，0–100 |
| `AddState(state_id, chance=100)` | 添加状态；ID 0 为普通攻击状态 |
| `RemoveState(state_id, chance=100)` | 移除状态 |
| `AddBuff(parameter, turns=3)` | 强化能力 |
| `AddDebuff(parameter, turns=3)` | 弱化能力 |
| `RemoveBuff(parameter)` | 移除强化 |
| `RemoveDebuff(parameter)` | 移除弱化 |
| `Escape()` | 逃跑 |
| `GrowParameter(parameter, amount)` | 永久提升能力，正整数 |
| `LearnSkill(skill_id)` | 学会技能 |
| `CommonEventEffect(common_event_id)` | 调用公共事件 |

百分比使用 25 表示 25%，不是 0.25。恢复百分比 -100–100，固定量 -999999–999999；状态概率 0–100。强化回合数 1–1000。
`parameter`：`max_hp`, `max_mp`, `attack`, `defense`, `magic_attack`, `magic_defense`, `agility`, `luck`。

```python
print(item.effects.list())
effect = item.effects.get(0)       # 下标从 0 开始；先核对类型再改属性
if isinstance(effect, RecoverHP):
    effect.amount = 200
item.effects.remove(0)
item.effects.clear()              # 明确需要移除全部效果时使用
item.bind_common_event(1205)       # 相同 ID 不重复追加，保留其他效果
```

绑定公共事件不会自动修改消耗性、范围、使用场合；按玩法设置。效果列表允许重复，并保持顺序。新增／修改的状态、技能、公共事件、动画及属性引用在预览时检查。

未知效果以 `OpaqueEffect` 保留；原有额外字段不丢失。通用字段读取返回副本，修改使用 `item.set(['插件字段', '子字段'], value)`，编码 JSON 路径仍支持 `{'decode': 'json'}`。此接口只替换已有字段，不允许修改物品 ID；更复杂的新增／删除扩展字段使用 `database.py`。调用 `set` 修改 effects 后重新获取效果对象。

支持读取、修改、创建和清空物品。清空不移除槽位、不移动后续 ID。测试覆盖字段、13 类效果、扩展字段、格式保留、备份恢复和冲突检查，不代表游戏运行测试。


## 创建、清空及引用查询

```python
item = db.items.create('药水')          # 追加至末尾，自动分配 ID
item = db.items.create('钥匙', id=91)   # 指定空槽；不覆盖非空物品
print(db.items.references(91))         # 显示引用文件、字段路径和用途
db.items.clear(91)                    # 重置为空白物品，保留编号
preview = db.preview()
print(preview)
db.commit(preview)
```

`create` 返回可编辑 Item。不指定 ID 时追加，不自动寻找空槽；指定 ID 允许 null 槽、标准空白记录或紧邻末尾的位置，不允许跨号创建。名称为空但其他字段有内容的记录不算空槽。需要覆盖时明确调用 `clear`。

`clear` 重置全部字段，包含备注、效果及插件扩展字段，不修改其他位置的引用。清空前用 `references` 检查影响；不会自动阻止清空。

`references(id)` 返回可打印和遍历的报告。每条结果提供 `file`、`path`、`usage`；路径中的页和指令下标从 0 开始。扫描磁盘中的公共事件、地图事件、战斗事件，覆盖更改物品、持有条件、商店商品、变量取得物品数量，以及地图页出现条件和敌人掉落。脚本、公式、插件参数及备注中的动态引用不解析，未提交修改不纳入扫描；缺失文件会提示，不能用无结果证明无引用。
