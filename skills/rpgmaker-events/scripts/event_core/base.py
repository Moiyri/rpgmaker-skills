"""事件命令与条件的基础协议。"""
from __future__ import annotations

from typing import Any, Literal, TypeVar

class Command:
    """事件命令基类。

    子类实现 to_spec；在所属 EventList 编译时验证参数与上下文。
    """

    def to_spec(self) -> dict[str, Any]:
        """返回命令的语义字典。

        基类未实现，调用时抛出 NotImplementedError。
        """
        raise NotImplementedError


class Condition:
    """条件基类。

    子类实现 to_spec，供 If 编译条件参数。
    """

    def to_spec(self) -> dict[str, Any]:
        """返回条件的语义字典。

        基类未实现，调用时抛出 NotImplementedError。
        """
        raise NotImplementedError


Comparison = Literal["eq", "ne", "ge", "le", "gt", "lt"]
Operation = Literal["set", "add", "sub", "mul", "div", "mod"]
EditOperation = Literal["replace_all", "append", "insert_before", "insert_after", "replace"]
CommandT = TypeVar("CommandT", bound=Command)
