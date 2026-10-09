"""Advanced（高级）指令。"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any
from ..base import Command
from .. import compiler as core


@dataclass(eq=False)
class Script(Command):
    """Script（脚本），在游戏运行时执行 JavaScript。

    text -- 脚本字符串，支持多行。编译器只存储，不执行或检查 JS 语法。
    必须按工程实际 API 编写；运行错误会影响事件执行。
    """

    text: str

    def to_spec(self) -> dict[str, Any]:
        """返回脚本内容，不执行脚本。"""
        return {'type': 'script', 'text': self.text}



@dataclass(eq=False)
class PluginCommand(Command):
    """Plugin Command（插件命令），调用 MZ 插件注册的命令。

    plugin -- 插件名，可含工程内子目录，不含 .js。
    command -- 注册命令 ID，不是编辑器显示名称。
    args -- 参数名到字符串值的字典；数字、布尔值、结构体也必须编码为字符串。
    display_name -- 编辑器命令名称，省略时使用 command。
    argument_labels -- 参数名到编辑器标签的字典，省略时使用参数名。

    先调用 plugin_help(project, plugin) 查询命令及参数声明，不能猜测参数。
    工具不执行插件，不自动校验命令注册或填充默认值；不支持旧 MV 命令 356。
    """

    plugin: str
    command: str
    args: dict[str, str]
    display_name: str | None = None
    argument_labels: dict[str, str] | None = None

    def to_spec(self) -> dict[str, Any]:
        """返回插件调用和编辑器说明行，参数不会自动转型。"""
        core.require(isinstance(self.args,dict) and all(isinstance(k,str) and isinstance(v,str) for k,v in self.args.items()),
                     'Plugin arguments must be string keys and string values')
        labels = self.argument_labels
        core.require(labels is None or (isinstance(labels,dict) and all(isinstance(k,str) and isinstance(v,str) for k,v in labels.items()) and labels.keys() <= self.args.keys()),
                     'Argument labels must refer to existing string argument keys')
        if hasattr(self,'_original_args') and core.db.equal(self.args,self._original_args) and core.db.equal(labels,self._original_labels):
            annotations = deepcopy(self._original_annotations)
        else:
            core.require(not getattr(self,'_unmapped_annotations',False) or
                         (labels is not None and labels.keys()==self.args.keys()),
                         'Nonstandard parameter display; provide complete argument_labels before changing args')
            annotations = [f'{(labels or {}).get(k,k)} = {v}' for k,v in self.args.items()]
        return {'type':'plugin_command','plugin':self.plugin,'command':self.command,
                'display_name':self.command if self.display_name is None else self.display_name,
                'args':deepcopy(self.args),'annotations':annotations}

    @classmethod
    def from_commands(cls, commands: list[dict[str, Any]]) -> PluginCommand:
        """读取 357 和 657 说明行；原样保留不能自动映射的显示文本。"""
        core.require(commands and commands[0]['code']==357,'Expected plugin command')
        p=commands[0]['parameters'];core.require(len(p)==4,'Expected four MZ plugin parameters')
        annotations=[]
        for c in commands[1:]:
            core.require(c['code']==657 and len(c['parameters'])==1,'Expected plugin argument description')
            annotations.append(core.string(c['parameters'][0]))
        node=cls(p[0],p[1],deepcopy(p[3]),p[2])
        node.to_spec()  # Validate argument types before attempting label inference.
        labels={}
        mapped=len(annotations)==len(node.args)
        if mapped:
            for (key,value),text in zip(node.args.items(),annotations):
                suffix=' = '+value
                if not text.endswith(suffix): mapped=False;break
                labels[key]=text[:-len(suffix)]
        node.argument_labels=labels if mapped else None
        node._original_args=deepcopy(node.args)
        node._original_labels=deepcopy(node.argument_labels)
        node._original_annotations=annotations
        node._unmapped_annotations=not mapped and bool(annotations)
        return node

