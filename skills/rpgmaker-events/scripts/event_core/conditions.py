"""条件对象及可读构造接口。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal
from .base import Condition, Comparison
from .operands import Constant, VariableValue
from . import compiler as core

@dataclass
class SwitchCondition(Condition):
    """表示开关状态条件。

    id -- 开关 ID，从 1 开始。
    on -- True 判断开启，False 判断关闭。
    """

    id: int
    on: bool = True
    def to_spec(self) -> dict[str, Any]:
        """返回该对象的语义字典，供事件编译器使用。"""
        return {'type': 'switch', 'id': self.id, 'on': self.on}


@dataclass
class VariableCondition(Condition):
    """比较游戏变量与常量或另一个变量。

    id -- 被比较的变量 ID，从 1 开始。
    comparison -- eq、ne、ge、le、gt 或 lt，分别表示等于、不等于、
        大于等于、小于等于、大于、小于。
    value -- 数字、Constant 或 VariableValue；数字表示常量。
    """

    id: int
    comparison: Comparison
    value: int | float | Constant | VariableValue
    def to_spec(self) -> dict[str, Any]:
        """返回该对象的语义字典，供事件编译器使用。"""
        value = Constant(self.value) if type(self.value) in (int, float) else self.value
        core.require(isinstance(value, (Constant, VariableValue)), 'Comparison requires a number, Constant or VariableValue')
        return {'type': 'variable', 'id': self.id, 'compare': self.comparison,
                'value_type': value.to_spec()['type'], 'value': value.to_spec()['value']}


@dataclass
class ScriptCondition(Condition):
    """使用 JavaScript 表达式作为条件。

    expression -- 表达式字符串，仅保存，由游戏运行时判断真假。
    """

    expression: str
    def to_spec(self) -> dict[str, Any]:
        """返回该对象的语义字典，供事件编译器使用。"""
        return {'type': 'script', 'expression': self.expression}


@dataclass
class SelfSwitchCondition(Condition):
    """判断当前地图事件的独立开关；没有事件上下文时条件不成立。"""

    key: Literal['A', 'B', 'C', 'D']
    on: bool

    def to_spec(self) -> dict[str, Any]:
        """返回独立开关条件的语义描述。"""
        return {'type': 'self_switch', 'key': self.key, 'on': self.on}


@dataclass
class SelfSwitch:
    """构造独立开关条件；key 为 A、B、C 或 D。

    使用解释器当前地图和事件 ID；公共事件取决于调用上下文，
    不是公共事件自身 ID。无地图事件上下文时，ON/OFF 判断都不成立。
    """

    key: Literal['A', 'B', 'C', 'D']

    def is_on(self) -> SelfSwitchCondition:
        """返回当前事件独立开关开启的条件。"""
        return SelfSwitchCondition(self.key, True)

    def is_off(self) -> SelfSwitchCondition:
        """返回当前事件独立开关关闭的条件。"""
        return SelfSwitchCondition(self.key, False)


@dataclass
class DirectionCondition(Condition):
    """判断地图人物朝向；direction 为 down、left、right 或 up。"""

    id: int
    direction: Literal['down', 'left', 'right', 'up']

    def to_spec(self) -> dict[str, Any]:
        """返回地图人物朝向条件的语义描述。"""
        return {'type': 'direction', 'id': self.id, 'direction': self.direction}


@dataclass
class Character:
    """构造地图人物条件，不使用数据库角色 ID。

    id -- -1 表示玩家，0 表示本事件，正整数表示当前地图事件 ID。
    """

    id: int

    def facing(self, direction: Literal['down', 'left', 'right', 'up']) -> DirectionCondition:
        """返回人物面向指定方向的条件。"""
        return DirectionCondition(self.id, direction)


@dataclass
class ItemCondition(Condition):
    """判断队伍是否持有数据库物品；id 从 1 开始，不含武器和防具。"""

    id: int

    def to_spec(self) -> dict[str, Any]:
        """返回物品持有条件的语义描述。"""
        return {'type': 'item', 'id': self.id}


@dataclass
class Item:
    """构造物品持有条件；id 为 Items 数据库 ID，从 1 开始。"""

    id: int

    def is_owned(self) -> ItemCondition:
        """返回队伍持有该物品的条件。"""
        return ItemCondition(self.id)


@dataclass
class ButtonCondition(Condition):
    """判断引擎按钮状态，按下、刚按下和重复按下分别编码。"""

    key: str
    mode: Literal['pressed', 'triggered', 'repeated']

    def to_spec(self) -> dict[str, Any]:
        """返回按钮条件的语义描述。"""
        return {'type': 'button', 'key': self.key, 'mode': self.mode}


@dataclass
class Button:
    """构造逻辑按钮条件，不使用键盘物理键名。

    key -- ok、cancel、shift、down、left、right、up、pageup 或 pagedown。
    具体键盘或手柄映射由工程 Input 配置决定。
    """

    key: str

    def is_pressed(self) -> ButtonCondition:
        """返回按钮处于按住状态的条件。"""
        return ButtonCondition(self.key, 'pressed')

    def is_triggered(self) -> ButtonCondition:
        """返回按钮在当前帧刚按下的条件。"""
        return ButtonCondition(self.key, 'triggered')

    def is_repeated(self) -> ButtonCondition:
        """返回刚按下或长按达到重复间隔的条件。"""
        return ButtonCondition(self.key, 'repeated')


@dataclass
class ActorCondition(Condition):
    """判断角色是否在队伍中，或姓名是否匹配。

    id -- 角色 ID，从 1 开始。
    test -- in_party 或 name；name 测试要求姓名字符串。
    """

    id: int
    test: Literal['in_party', 'name']
    name: str | None = None

    def to_spec(self) -> dict[str, Any]:
        """返回角色条件参数的语义描述。"""
        spec = {'type': 'actor', 'id': self.id, 'test': self.test}
        if self.name is not None:
            spec['name'] = self.name
        return spec


@dataclass
class Actor:
    """构造角色条件；id 为从 1 开始的角色 ID。"""

    id: int

    def in_party(self) -> ActorCondition:
        """返回角色属于当前队伍的条件。"""
        return ActorCondition(self.id, 'in_party')

    def name_equals(self, name: str) -> ActorCondition:
        """返回角色姓名严格等于 name 字符串的条件。"""
        return ActorCondition(self.id, 'name', name)


@dataclass
class Switch:
    """构造开关状态条件。

    id -- 开关 ID，从 1 开始。调用 is_on 或 is_off 得到供 If 使用的条件。
    """

    id: int
    def is_on(self) -> SwitchCondition:
        """返回判断该开关开启的条件。"""
        return SwitchCondition(self.id, True)
    def is_off(self) -> SwitchCondition:
        """返回判断该开关关闭的条件。"""
        return SwitchCondition(self.id, False)


@dataclass
class Variable:
    """构造变量比较条件。

    id -- 变量 ID，从 1 开始。各比较方法接受数字、Constant 或
    VariableValue；数字表示常量，返回供 If 使用的条件。
    """

    id: int
    def equal_to(self, value: int | float | Constant | VariableValue) -> VariableCondition:
        """返回判断该变量等于 value 的条件。

        value -- 数字、Constant 或 VariableValue；数字表示常量。
        """
        return VariableCondition(self.id, 'eq', value)
    def not_equal_to(self, value: int | float | Constant | VariableValue) -> VariableCondition:
        """返回判断该变量不等于 value 的条件。

        value -- 数字、Constant 或 VariableValue；数字表示常量。
        """
        return VariableCondition(self.id, 'ne', value)
    def greater_or_equal(self, value: int | float | Constant | VariableValue) -> VariableCondition:
        """返回判断该变量大于等于 value 的条件。

        value -- 数字、Constant 或 VariableValue；数字表示常量。
        """
        return VariableCondition(self.id, 'ge', value)
    def less_or_equal(self, value: int | float | Constant | VariableValue) -> VariableCondition:
        """返回判断该变量小于等于 value 的条件。

        value -- 数字、Constant 或 VariableValue；数字表示常量。
        """
        return VariableCondition(self.id, 'le', value)
    def greater_than(self, value: int | float | Constant | VariableValue) -> VariableCondition:
        """返回判断该变量大于 value 的条件。

        value -- 数字、Constant 或 VariableValue；数字表示常量。
        """
        return VariableCondition(self.id, 'gt', value)
    def less_than(self, value: int | float | Constant | VariableValue) -> VariableCondition:
        """返回判断该变量小于 value 的条件。

        value -- 数字、Constant 或 VariableValue；数字表示常量。
        """
        return VariableCondition(self.id, 'lt', value)
