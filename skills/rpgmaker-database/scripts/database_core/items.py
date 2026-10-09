"""物品列表、物品属性与伤害设置。"""
from copy import deepcopy
from .backend import db, integer
from .effects import Effects, CommonEventEffect

ITEM_TYPES={1:'regular',2:'key_item',3:'hidden_a',4:'hidden_b'}
SCOPES=dict(enumerate(['none','one_enemy','all_enemies','random_1_enemy','random_2_enemies','random_3_enemies','random_4_enemies','one_ally','all_allies','one_dead_ally','all_dead_allies','user','one_ally_any','all_allies_any','everyone']))
OCCASIONS={0:'always',1:'battle',2:'menu',3:'never'}
HIT_TYPES={0:'certain',1:'physical',2:'magical'}
DAMAGE_TYPES=dict(enumerate(['none','hp_damage','mp_damage','hp_recover','mp_recover','hp_drain','mp_drain']))


class Field:
    def __init__(self,key,kind,low=0,high=None,choices=None):
        self.key,self.kind,self.low,self.high,self.choices=key,kind,low,high,choices
        self.__doc__ = (', '.join(choices.values()) if choices else f'{kind.__name__}; {low}..{high}' if kind is int else kind.__name__)
    def __get__(self,obj,owner):
        if obj is None:return self
        value=obj._data[self.key]
        return self.choices.get(value,value) if self.choices else deepcopy(value)
    def __set__(self,obj,value):
        if self.choices:
            db.require(isinstance(value,str) and value in self.choices.values(),f'{self.key}: expected {list(self.choices.values())}')
            value=next(k for k,v in self.choices.items() if v==value)
        elif self.kind is int:integer(value,self.low,self.high)
        else:db.require(type(value) is self.kind,f'{self.key}: expected {self.kind.__name__}')
        obj._data[self.key]=value


class Damage:
    """伤害设置。type 使用 DAMAGE_TYPES；element_id=-1 普通攻击、0 无属性。

    formula 为 JavaScript 表达式，variance 为 0–100，critical 为 bool。
    公式只作为字符串保存，不进行求值。
    """
    type=Field('type',str,choices=DAMAGE_TYPES)
    element_id=Field('elementId',int,-1)
    formula=Field('formula',str)
    variance=Field('variance',int,0,100)
    critical=Field('critical',bool)
    def __init__(self,owner):self._owner=owner
    @property
    def _data(self):return self._owner._data['damage']


class Item:
    """已有物品。id 只读，属性按编辑器含义命名；effects 为有序效果对象列表。

    item_type: regular/key_item/hidden_a/hidden_b。
    occasion: always/battle/menu/never；hit_type: certain/physical/magical。
    scope 的可选名称见 SCOPES。普通字段保留本地化占位文字，不自动翻译。
    """
    name=Field('name',str)
    description=Field('description',str)
    icon_index=Field('iconIndex',int)
    item_type=Field('itypeId',str,choices=ITEM_TYPES)
    price=Field('price',int)
    consumable=Field('consumable',bool)
    scope=Field('scope',str,choices=SCOPES)
    occasion=Field('occasion',str,choices=OCCASIONS)
    speed=Field('speed',int,-2000,2000)
    success_rate=Field('successRate',int,0,100)
    repeats=Field('repeats',int,1,9)
    tp_gain=Field('tpGain',int,0,100)
    hit_type=Field('hitType',str,choices=HIT_TYPES)
    animation_id=Field('animationId',int,-1)
    note=Field('note',str)

    def __init__(self,data):
        self._data=deepcopy(data)
        self._effects=Effects(self._data['effects'])
    @property
    def id(self):return self._data['id']
    @property
    def damage(self):return Damage(self)
    @property
    def effects(self):return self._effects
    def to_data(self):
        value=deepcopy(self._data);value['effects']=self.effects.to_data();return value
    def get(self,path):
        """读取任意嵌套字段的副本，path 如 ['damage','formula']；支持后端 decode 路径。"""
        return deepcopy(db.get(self.to_data(),path))
    def set(self,path,value):
        """修改已有字段，支持嵌套及编码 JSON 路径；id 不可修改。"""
        db.require(isinstance(path,list) and path and path[0]!='id','Cannot replace item root or ID')
        data=db.apply_operation(self.to_data(),{'op':'set','file':'Items.json','path':path,'value':deepcopy(value)})
        self._data=data
        if path[0]=='effects':self._effects=Effects(data['effects'])
    def bind_common_event(self,id):
        """追加公共事件效果，保留其他效果；同一 ID 已绑定时不重复追加。"""
        integer(id,1)
        if not any(isinstance(e,CommonEventEffect) and e.common_event_id==id for e in self.effects):
            self.effects.add(CommonEventEffect(id))
    def describe(self):
        """显示所有普通字段、伤害设置、效果及扩展字段名称。"""
        lines=[f'{self.id:04d} {self.name}']
        lines.extend(f'{name}: {getattr(self,name)!r}' for name,field in vars(Item).items() if isinstance(field,Field) and name!='name')
        lines.extend(f'damage.{name}: {getattr(self.damage,name)!r}' for name,field in vars(Damage).items() if isinstance(field,Field))
        lines.append('effects:\n'+self.effects.list())
        known={f.key for f in vars(Item).values() if isinstance(f,Field)}|{'id','damage','effects'}
        lines.append('扩展字段: '+', '.join(k for k in self._data if k not in known))
        return '\n'.join(lines)


class Items:
    """物品集合；创建和清空记录，不移动已有 ID。"""
    def __init__(self,owner):self._owner=owner;self._cache={};self._working=deepcopy(owner._items)
    def get(self,id):
        """按 ID 获取可编辑物品，包括未命名的编辑器空记录；null 槽位报错。"""
        integer(id,1,len(self._working)-1)
        value=self._working[id]
        db.require(isinstance(value,dict) and value.get('id')==id,'Missing item or mismatched ID')
        if id not in self._cache:self._cache[id]=Item(value)
        return self._cache[id]
    def _rows(self):
        for i,data in enumerate(self._working):
            if i and data is not None:yield self.get(i)
    def list(self, *, include_empty=False, offset=0, limit=50):
        """返回物品 ID、原始名称、类型与消耗性的简短文本；默认跳过未命名记录。"""
        integer(offset);integer(limit,1)
        rows=[i for i in self._rows() if include_empty or i.name]
        return '\n'.join([f'物品 {len(rows)} 项，显示 {offset} 起最多 {limit} 项']+[f'{i.id:04d} {i.name or "（未命名）"} | {i.item_type} | 消耗={i.consumable}' for i in rows[offset:offset+limit]])
    def find(self,text):
        """按原始名称子串搜索，忽略大小写；返回可编辑 Item 列表。"""
        db.require(isinstance(text,str),'Expected search text')
        return [i for i in self._rows() if text.casefold() in i.name.casefold()]

    def create(self, name='', id=None):
        """创建物品并返回 Item；省略 ID 则追加，指定 ID 只能是空槽或末尾。"""
        db.require(isinstance(name,str),'Expected name string')
        target=len(self._working) if id is None else integer(id,1,len(self._working))
        if target<len(self._working):
            current=self._cache[target].to_data() if target in self._cache else self._working[target]
            db.require(current is None or db.equal(current,blank_item(target)),'Target item is not empty; clear it explicitly first')
        value=blank_item(target);value['name']=name
        if target==len(self._working):self._working.append(value)
        else:self._working[target]=value
        if target in self._cache:
            node=self._cache[target];node._data=deepcopy(value);node._effects=Effects([])
        else:self._cache[target]=Item(value)
        return self._cache[target]

    def clear(self, id):
        """重置为编辑器空白物品，保留 ID；同时移除效果和插件字段，不修改引用。"""
        node=self.get(id)
        node._data=blank_item(id);node._effects=Effects([])
        return node

    def references(self, id):
        """查询磁盘工程中的原生物品引用；返回可打印、可遍历的报告。"""
        from .references import find_item_references
        integer(id,1)
        return find_item_references(self._owner.root,id)


def blank_item(id):
    """RPG Maker 编辑器空白物品默认值。"""
    return dict(id=id,animationId=0,consumable=True,
                damage=dict(critical=False,elementId=0,formula='0',type=0,variance=20),
                description='',effects=[],hitType=0,iconIndex=0,itypeId=1,name='',note='',
                occasion=0,price=0,repeats=1,scope=7,speed=0,successRate=100,tpGain=0)
