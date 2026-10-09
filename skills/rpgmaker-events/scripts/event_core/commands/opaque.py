"""未支持指令的原始块保留。"""
from __future__ import annotations

from copy import deepcopy
from typing import Any
from ..base import Command


class OpaqueCommand(Command):
    """表示尚未解码的原始指令；只能随原事件原样保留。

    不提供内部参数修改接口。复杂指令块作为整体保留，重新编译时统一调整缩进。
    """

    def __init__(self, commands: list[dict[str, Any]]) -> None:
        """保存原始指令的独立副本。"""
        self._raw = deepcopy(commands)

    def to_spec(self) -> dict[str, Any]:
        """返回携带原始指令块的语义表示，保留未知参数。"""
        return {'type': 'raw', 'commands': deepcopy(self._raw)}

