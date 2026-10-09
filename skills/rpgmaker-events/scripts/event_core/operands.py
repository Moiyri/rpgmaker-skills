"""变量操作数对象；不执行游戏脚本。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

@dataclass
class Constant:
    """表示数值常量。

    value -- 整数或有限浮点数，不接受布尔值。
    """

    value: int | float
    def to_spec(self) -> dict[str, Any]:
        """返回该对象的语义字典，供事件编译器使用。"""
        return {'type': 'constant', 'value': self.value}


@dataclass
class VariableValue:
    """读取另一个游戏变量的值。

    id -- 来源变量 ID，从 1 开始。
    """

    id: int
    def to_spec(self) -> dict[str, Any]:
        """返回该对象的语义字典，供事件编译器使用。"""
        return {'type': 'variable', 'value': self.id}


@dataclass
class RandomValue:
    """表示闭区间内的随机整数。

    minimum -- 最小整数。
    maximum -- 最大整数，不小于 minimum。

    随机值由游戏运行时产生，编译时不抽样。
    """

    minimum: int
    maximum: int
    def to_spec(self) -> dict[str, Any]:
        """返回该对象的语义字典，供事件编译器使用。"""
        return {'type': 'random', 'min': self.minimum, 'max': self.maximum}


@dataclass
class ScriptValue:
    """使用 JavaScript 表达式作为变量操作数。

    expression -- 表达式字符串，仅保存，由游戏运行时执行。

    Game Data（游戏数据）使用本接口读取；表达式须按工程实际 JS API 编写。
    例如读取金币：ScriptValue("$gameParty.gold()")。
    提供返回所需值的表达式，不在表达式中重复执行变量赋值。
    """

    expression: str
    def to_spec(self) -> dict[str, Any]:
        """返回该对象的语义字典，供事件编译器使用。"""
        return {'type': 'script', 'value': self.expression}
