"""Message（消息）指令。"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any
from typing import Literal
from ..base import Command
from .. import compiler as core


@dataclass(eq=False)
class ShowText(Command):
    """Show Text（显示文字），显示一个对话窗口。

    lines -- 一行文字或 1–4 行文字列表，每行不含换行符。
    speaker -- 姓名，默认空。
    face -- 脸图文件名，不含扩展名，默认空。
    face_index -- 脸图下标 0–7，默认 0。
    background -- window / dim / transparent，默认 window。
    position -- top / middle / bottom，默认 bottom。
    """

    lines: str | list[str]
    speaker: str = ''
    face: str = ''
    face_index: int = 0
    background: Literal["window", "dim", "transparent"] = 'window'
    position: Literal["top", "middle", "bottom"] = 'bottom'
    def to_spec(self) -> dict[str, Any]:
        """返回该对象的语义字典，供事件编译器使用。"""
        return {'type': 'text', 'lines': [self.lines] if isinstance(self.lines, str) else self.lines,
                'speaker': self.speaker, 'face': self.face, 'face_index': self.face_index,
                'background': core.enum(self.background, ['window', 'dim', 'transparent']),
                'position': core.enum(self.position, ['top', 'middle', 'bottom'])}

    @classmethod
    def from_commands(cls, commands: list[dict[str, Any]]) -> ShowText:
        """从一组 101 和连续 401 指令读取一个对话窗口。

        commands -- 仅包含一个窗口，不含事件结束标记。所有指令缩进相同，
            101 至少有五个 MZ 参数，401 至少有一个文本参数。

        返回独立对象，不修改输入。无法表示的参数或非 1–4 行文本抛出
        ValueError。额外参数和字段保存在内部，供所在事件往返编译使用。
        """
        core.require(isinstance(commands, list) and 2 <= len(commands) <= 5,
                     'ShowText requires one 101 and 1..4 continuation commands')
        raw = deepcopy(commands)
        for i, item in enumerate(raw):
            core.require(isinstance(item, dict), 'Command must be an object')
            core.require(type(item.get('code')) is int and item['code'] == (101 if i == 0 else 401),
                         'Expected 101 followed by 401')
            core.integer(item.get('indent'))
            core.require(item['indent'] == raw[0]['indent'], 'Message continuation indent mismatch')
            core.require(isinstance(item.get('parameters'), list) and
                         len(item['parameters']) >= (5 if i == 0 else 1), 'Missing message parameters')
        params = raw[0]['parameters']
        core.integer(params[2], 0, 2); core.integer(params[3], 0, 2)
        node = cls([c['parameters'][0] for c in raw[1:]], speaker=params[4],
                   face=params[0], face_index=params[1],
                   background=['window', 'dim', 'transparent'][params[2]],
                   position=['top', 'middle', 'bottom'][params[3]])
        core.compile_nodes([node.to_spec()])
        node._source_commands = raw
        node._source_spec = deepcopy(node.to_spec())
        return node

    def _encode_source(self) -> list[dict[str, Any]]:
        spec = self.to_spec()
        # Validate edited fields through the same compiler used for new commands.
        generated = core.compile_nodes([spec], self._source_commands[0]['indent'])
        if core.db.equal(spec, self._source_spec):
            return deepcopy(self._source_commands)
        raw = deepcopy(self._source_commands)
        raw[0]['parameters'][:5] = generated[0]['parameters']
        lines = []
        for index, item in enumerate(generated[1:], 1):
            if index < len(raw):
                existing = raw[index]
                existing['parameters'][0] = item['parameters'][0]
                lines.append(existing)
            else:
                lines.append(item)
        return [raw[0], *lines]



class ShowChoices(Command):
    """Show Choices（显示选项），choices 为 (文字, 指令列表) 序列，1–6 项。

    default 为默认项下标；cancel 为取消时选择的下标，-1 禁止取消。
    本接口暂不支持独立取消分支。下标从 0 开始。
    """
    def __init__(self, choices, *, default=0, cancel=-1):
        from .flow_control import as_list
        self.choices = [(text, as_list(body)) for text, body in choices]
        self.default = default
        self.cancel = cancel

    def to_spec(self):
        return {'type':'choices','choices':[{'text':text,'body':body.to_spec()} for text,body in self.choices],
                'default':self.default,'cancel':self.cancel}
