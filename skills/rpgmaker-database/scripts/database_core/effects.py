"""物品效果：具名参数与引擎 code/dataId/value1/value2 的转换。"""
from dataclasses import dataclass, fields
from copy import deepcopy
from .backend import db, integer, number, index

PARAMETERS = ['max_hp','max_mp','attack','defense','magic_attack','magic_defense','agility','luck']


class Effect:
    """效果基类；使用具体效果对象添加到 item.effects。"""
    def to_data(self):
        values={f.name:getattr(self,f.name) for f in fields(self)}
        if hasattr(self,'_original_values') and db.equal(values,self._original_values):
            return deepcopy(self._original_raw)
        code=next(k for k,c in TYPES.items() if type(self) is c)
        data_id=0;v1=0;v2=0
        if code in (11,12):
            v1=number(self.percent,-100,100)/100;v2=integer(self.amount,-999999,999999)
        elif code==13:v1=integer(self.amount,0,100)
        elif code in (21,22):
            data_id=integer(self.state_id,0 if code==21 else 1);v1=number(self.chance,0,100)/100
        elif code in (31,32,33,34,42):
            db.require(self.parameter in PARAMETERS,'Unknown parameter')
            data_id=PARAMETERS.index(self.parameter)
            if code in (31,32):v1=integer(self.turns,1,1000)
            elif code==42:v1=integer(self.amount,1)
        elif code==43:data_id=integer(self.skill_id,1)
        elif code==44:data_id=integer(self.common_event_id,1)
        raw=deepcopy(getattr(self,'_original_raw',{}))
        raw.update(code=code,dataId=data_id,value1=v1,value2=v2)
        return raw


@dataclass
class RecoverHP(Effect):
    """恢复 HP：最大 HP 的 percent% 加 amount；负数表示减少，percent 为 -100–100。"""
    percent: float = 0
    amount: int = 0


@dataclass
class RecoverMP(Effect):
    """恢复 MP：最大 MP 的 percent% 加 amount；负数表示减少。"""
    percent: float = 0
    amount: int = 0


@dataclass
class GainTP(Effect):
    """增加 TP，amount 为 0–100。"""
    amount: int = 0


@dataclass
class AddState(Effect):
    """添加状态，chance 为百分比 0–100；state_id=0 表示普通攻击状态。"""
    state_id: int
    chance: float = 100


@dataclass
class RemoveState(Effect):
    """移除状态，chance 为百分比 0–100。"""
    state_id: int
    chance: float = 100


@dataclass
class AddBuff(Effect):
    """添加强化，parameter 使用 PARAMETERS 的名称，turns 为持续回合数。"""
    parameter: str
    turns: int = 3


@dataclass
class AddDebuff(Effect):
    """添加弱化，parameter 使用 PARAMETERS 的名称，turns 为持续回合数。"""
    parameter: str
    turns: int = 3


@dataclass
class RemoveBuff(Effect):
    """移除指定能力强化，例如 parameter='attack'。"""
    parameter: str


@dataclass
class RemoveDebuff(Effect):
    """移除指定能力弱化，例如 parameter='defense'。"""
    parameter: str


@dataclass
class Escape(Effect):
    """特殊效果：逃跑。"""


@dataclass
class GrowParameter(Effect):
    """永久增加能力，amount 为正整数。"""
    parameter: str
    amount: int


@dataclass
class LearnSkill(Effect):
    """让目标学会 skill_id 技能。"""
    skill_id: int


@dataclass
class CommonEventEffect(Effect):
    """调用公共事件，common_event_id 为公共事件 ID。"""
    common_event_id: int


class OpaqueEffect(Effect):
    """未支持或非标准效果，保留原始字段；通过物品通用路径接口显式编辑。"""
    def __init__(self, raw):self._raw=deepcopy(raw)
    def to_data(self):return deepcopy(self._raw)


TYPES={11:RecoverHP,12:RecoverMP,13:GainTP,21:AddState,22:RemoveState,31:AddBuff,32:AddDebuff,
       33:RemoveBuff,34:RemoveDebuff,41:Escape,42:GrowParameter,43:LearnSkill,44:CommonEventEffect}


def decode_effect(raw):
    try:
        code=raw['code'];d=raw['dataId'];v1=raw['value1'];v2=raw['value2']
        if type(code) is not int or code not in TYPES:raise ValueError()
        cls=TYPES[code]
        if code in (11,12):node=cls(v1*100,v2)
        elif code==13:node=cls(v1)
        elif code in (21,22):node=cls(d,v1*100)
        elif code in (31,32):node=cls(PARAMETERS[index(d,8)],v1)
        elif code in (33,34):node=cls(PARAMETERS[index(d,8)])
        elif code==41:node=cls()
        elif code==42:node=cls(PARAMETERS[index(d,8)],v1)
        else:node=cls(d)
        canonical=node.to_data()
        # Tolerate floating-point percentage conversion only; retain exact original values.
        for k,v in canonical.items():
            actual=raw[k]
            if k=='value1' and code in (11,12,21,22) and type(actual) in (int,float):
                db.require(abs(actual-v)<1e-12,'Noncanonical effect')
            else:db.require(db.equal(actual,v),'Noncanonical effect')
        node._original_raw=deepcopy(raw)
        node._original_values={f.name:getattr(node,f.name) for f in fields(node)}
        return node
    except (KeyError,TypeError,ValueError,IndexError):return OpaqueEffect(raw)


class Effects:
    """有序效果列表；下标从 0 开始，允许重复类型。"""
    def __init__(self, raw):
        db.require(isinstance(raw,list),'effects must be a list')
        self._values=[decode_effect(v) for v in raw]
    def __len__(self):return len(self._values)
    def __iter__(self):return iter(self._values)
    def get(self, i):
        """返回可修改的效果对象。"""
        return self._values[index(i,len(self._values))]
    def add(self, effect):
        """追加效果并返回该对象。"""
        db.require(isinstance(effect,Effect),'Expected Effect');effect.to_data()
        self._values.append(effect);return effect
    def remove(self, i):
        """按下标移除一条效果。"""
        return self._values.pop(index(i,len(self._values)))
    def clear(self):
        """清空全部效果。"""
        self._values.clear()
    def list(self):
        """返回简短文本列表。"""
        return '\n'.join(f'{i}: {v!r}' if not isinstance(v,OpaqueEffect) else f'{i}: 未识别效果 code={v._raw.get("code")}' for i,v in enumerate(self._values)) or '无效果'
    def to_data(self):return [v.to_data() for v in self._values]
