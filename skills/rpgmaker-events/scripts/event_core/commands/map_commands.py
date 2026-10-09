"""Map（地图）指令。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from ..base import Command


@dataclass(eq=False)
class EraseEvent(Command):
    """Erase Event（暂时消除事件），消除当前地图事件。

    需要当前地图事件上下文；重新进入地图后事件可恢复，不会永久删除数据。
    不等于退出事件处理，后续指令仍可能继续执行。
    """

    def to_spec(self) -> dict[str, Any]:
        """返回暂时消除事件指令。"""
        return {'type': 'erase_event'}

