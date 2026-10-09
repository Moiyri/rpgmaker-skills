"""Party（队伍）指令。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import Literal
from ..base import Command
from ..operands import Constant
from ..operands import VariableValue
from .. import compiler as core


@dataclass(eq=False)
class ChangeGold(Command):
    """Change Gold（更改金币），增加或减少队伍金币。

    value -- Constant（非负整数）或 VariableValue。
    operation -- add / sub，默认 add；变量值的正负由游戏运行时决定。
    """

    value: Constant | VariableValue
    operation: Literal['add', 'sub'] = 'add'

    def to_spec(self) -> dict[str, Any]:
        """返回金币操作。"""
        core.require(isinstance(self.value, (Constant, VariableValue)), 'Amount requires Constant or VariableValue')
        return {'type': 'gold', 'operation': self.operation, 'value': self.value.to_spec()}



@dataclass(eq=False)
class ChangeItems(Command):
    """Change Items（更改物品），增加或减少物品数量。

    id -- Items 数据库 ID，从 1 开始，不是武器或防具 ID。
    value -- Constant（非负整数）或 VariableValue。
    operation -- add / sub，默认 add。
    """

    id: int
    value: Constant | VariableValue
    operation: Literal['add', 'sub'] = 'add'

    def to_spec(self) -> dict[str, Any]:
        """返回物品操作。"""
        core.require(isinstance(self.value, (Constant, VariableValue)), 'Amount requires Constant or VariableValue')
        return {'type': 'items', 'id': self.id, 'operation': self.operation, 'value': self.value.to_spec()}

