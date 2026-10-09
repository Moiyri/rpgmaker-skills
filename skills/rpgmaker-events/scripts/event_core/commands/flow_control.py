"""Flow Control（流程控制）指令。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import Iterable
from ..base import Command
from ..base import Condition
from .. import compiler as core
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..event_list import EventList


class If(Command):
    """Conditional Branch（条件分支），按条件执行对应的命令列表。

    condition -- 条件，如 Switch(1).is_on()。
    then -- 条件成立时执行的命令列表。
    otherwise -- 不成立时执行的命令列表；None 表示无否则，[] 表示空否则。
    """

    def __init__(self, condition: Condition, then: EventList | Iterable[Command] = (),
                 otherwise: EventList | Iterable[Command] | None = None) -> None:
        """保存条件和分支列表。"""
        self.condition = condition
        self.then = then
        self.otherwise = otherwise

    @property
    def then(self) -> EventList:
        """获取或设置条件成立时执行的 EventList。"""
        return self._then
    @then.setter
    def then(self, value: EventList | Iterable[Command]) -> None:
        """设置命令列表；可迭代对象转换为 EventList，已有 EventList 保留引用。"""
        self._then = as_list(value)
    @property
    def otherwise(self) -> EventList | None:
        """获取或设置否则分支；None 表示没有否则。"""
        return self._otherwise
    @otherwise.setter
    def otherwise(self, value: EventList | Iterable[Command] | None) -> None:
        """设置命令列表；可迭代对象转换为 EventList，已有 EventList 保留引用。"""
        self._otherwise = None if value is None else as_list(value)

    def to_spec(self) -> dict[str, Any]:
        """返回该对象的语义字典，供事件编译器使用。"""
        core.require(isinstance(self.condition, Condition), 'If requires a Condition')
        result = {'type': 'if', 'condition': self.condition.to_spec(), 'then': self.then.to_spec()}
        if self.otherwise is not None: result['else'] = self.otherwise.to_spec()
        return result



class Loop(Command):
    """Loop（循环），重复执行命令列表。

    body -- 循环内的命令列表。

    必须配合可执行到的 BreakLoop() 退出，否则会持续循环。
    """

    def __init__(self, body: EventList | Iterable[Command] = ()) -> None:
        """保存循环内的命令列表。"""
        self.body = body
    @property
    def body(self) -> EventList:
        """获取或设置循环体 EventList。"""
        return self._body
    @body.setter
    def body(self, value: EventList | Iterable[Command]) -> None:
        """设置命令列表；可迭代对象转换为 EventList，已有 EventList 保留引用。"""
        self._body = as_list(value)
    def to_spec(self) -> dict[str, Any]:
        """返回该对象的语义字典，供事件编译器使用。"""
        return {'type': 'loop', 'body': self.body.to_spec()}



@dataclass(eq=False)
class BreakLoop(Command):
    """Break Loop（退出循环），跳出所在的循环。

    放在 Loop 内使用，也可放在循环内的 If 分支中。
    """

    def to_spec(self) -> dict[str, Any]:
        """返回该对象的语义字典，供事件编译器使用。"""
        return {'type': 'break'}



@dataclass(eq=False)
class CommonEvent(Command):
    """Common Event（公共事件），调用指定公共事件。

    id -- 公共事件 ID，从 1 开始。
    """

    id: int
    def to_spec(self) -> dict[str, Any]:
        """返回该对象的语义字典，供事件编译器使用。"""
        return {'type': 'call', 'id': self.id}



@dataclass(eq=False)
class Comment(Command):
    """Comment（注释），保存单行或多行注释。

    text -- 字符串，换行自动拆成注释续行；不作为脚本执行。
    """

    text: str

    def to_spec(self) -> dict[str, Any]:
        """返回注释内容。"""
        return {'type': 'comment', 'text': self.text}



def as_list(value: EventList | Iterable[Command]) -> EventList:
    """将命令序列转换成列表，已有列表保留引用。"""
    from ..event_list import EventList
    return value if isinstance(value, EventList) else EventList(value)



@dataclass(eq=False)
class Label(Command):
    """Label（标签），为当前指令列表设置跳转位置；同一列表中名称应唯一。"""
    name: str
    def to_spec(self):
        return {'type':'label','name':self.name}


@dataclass(eq=False)
class JumpToLabel(Command):
    """Jump to Label（跳转标签），只跳转当前列表中的同名标签，不能跨公共事件。"""
    name: str
    def to_spec(self):
        return {'type':'jump_to_label','name':self.name}


class ExitEvent(Command):
    """Exit Event Processing（退出事件处理），结束当前事件；被调用的公共事件结束后调用者继续。"""
    def to_spec(self):
        return {'type':'exit_event'}
