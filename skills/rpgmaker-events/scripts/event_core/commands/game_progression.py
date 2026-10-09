"""Game Progression（游戏进程）指令。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import Literal
from ..base import Command
from ..base import Operation
from ..operands import Constant
from ..operands import VariableValue
from ..operands import RandomValue
from ..operands import ScriptValue
from .. import compiler as core


@dataclass(eq=False)
class SetSwitch(Command):
    """Control Switches（控制开关），开启或关闭指定开关。

    id -- 开关 ID，从 1 开始。
    on -- True 开启，False 关闭，默认 True。
    end -- 范围末尾 ID，包含两端；省略时只操作 id。
    """

    id: int
    on: bool = True
    end: int | None = None
    def to_spec(self) -> dict[str, Any]:
        """返回该对象的语义字典，供事件编译器使用。"""
        return {'type': 'switch', 'start': self.id, 'end': self.id if self.end is None else self.end, 'on': self.on}



@dataclass(eq=False)
class ChangeVariable(Command):
    """Control Variables（控制变量），给变量赋值或进行运算。

    id -- 变量 ID，从 1 开始。
    operation -- set / add / sub / mul / div / mod（赋值、加、减、乘、除、取模）。
    value -- Constant / VariableValue / RandomValue / ScriptValue。
    end -- 范围末尾 ID，包含两端；省略时只操作 id。

    Game Data（游戏数据）通过 ScriptValue 表达式读取，使用 set 赋值。
    """

    id: int
    operation: Operation
    value: Constant | VariableValue | RandomValue | ScriptValue
    end: int | None = None
    def to_spec(self) -> dict[str, Any]:
        """返回该对象的语义字典，供事件编译器使用。"""
        core.require(isinstance(self.value, (Constant, VariableValue, RandomValue, ScriptValue)),
                     'Variable operand must be Constant, VariableValue, RandomValue or ScriptValue')
        return {'type': 'variable', 'start': self.id, 'end': self.id if self.end is None else self.end,
                'operation': self.operation, 'operand': self.value.to_spec()}



@dataclass(eq=False)
class SetSelfSwitch(Command):
    """Control Self Switch（控制独立开关），开启或关闭本事件的独立开关。

    key -- A / B / C / D。
    on -- True 开启，False 关闭，默认 True。

    必须有地图事件上下文；公共事件使用调用者上下文，没有上下文时不生效。
    """

    key: Literal['A', 'B', 'C', 'D']
    on: bool = True

    def to_spec(self) -> dict[str, Any]:
        """返回独立开关指令的语义描述。"""
        return {'type': 'set_self_switch', 'key': self.key, 'on': self.on}



@dataclass(eq=False)
class StartTimer(Command):
    """Control Timer（控制计时器），开始倒计时。

    seconds -- 非负整数秒数。

    使用全局计时器；再次启动会覆盖原计时，不会等待倒计时结束。
    """

    seconds: int

    def to_spec(self) -> dict[str, Any]:
        """返回启动计时器指令的语义描述。"""
        return {'type': 'start_timer', 'seconds': self.seconds}



@dataclass(eq=False)
class StopTimer(Command):
    """Control Timer（控制计时器），停止全局倒计时。"""

    def to_spec(self) -> dict[str, Any]:
        """返回停止计时器指令的语义描述。"""
        return {'type': 'stop_timer'}

