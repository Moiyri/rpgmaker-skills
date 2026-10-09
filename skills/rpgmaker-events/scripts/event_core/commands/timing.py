"""Timing（计时）指令。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from ..base import Command


@dataclass(eq=False)
class Wait(Command):
    """Wait（等待），暂停当前事件指定帧数。

    frames -- 正整数帧数；引擎通常按 60 帧约一秒计算，不是毫秒。
    """

    frames: int

    def to_spec(self) -> dict[str, Any]:
        """返回等待帧数。"""
        return {'type': 'wait', 'frames': self.frames}

