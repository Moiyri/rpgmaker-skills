"""维护事件列表和节点编辑，委托编译器与解码器转换。"""
from __future__ import annotations

from typing import Any, Iterable, Iterator
from .base import Command, CommandT, EditOperation
from .commands.message import ShowChoices, ShowText
from .commands.flow_control import If, Loop
from .targets import locate
from . import compiler as core

class EventList:
    """维护可嵌套的事件命令列表。

    支持迭代、len 和下标读取。find 默认递归查找；相对编辑方法按对象身份
    定位，anchor 必须在整个查找范围中恰好出现一次，否则抛出 ValueError。
    每个位置应使用独立命令对象。替换或删除分支对象会同时移除其子列表。

    列表保留对象引用；直接修改命令属性会影响后续编译。compile 验证并返回
    完整指令数组，to_document 和 to_plan 导出语义数据。
    """

    def __init__(self, commands: Iterable[Command] = ()) -> None:
        """从命令可迭代对象创建列表。

        commands -- 按执行顺序提供 Command 对象，默认空；保留各命令引用。
        遇到非 Command 元素抛出 ValueError。
        """
        self._commands = []
        self.extend(commands)

    @classmethod
    def from_commands(cls, commands: list[dict[str, Any]]) -> EventList:
        """将完整引擎指令数组解码为可编辑的嵌套事件列表。

        支持文字、开关、变量、条件分支、公共事件调用、循环和退出循环。
        未支持的参数类型或指令块使用 OpaqueCommand 整体保留。
        无法确定控制流边界时抛出 ValueError，不猜测结构。
        保留原始快照，to_plan 自动绑定该快照的指纹。
        """
        from .decoder import decode_commands
        return decode_commands(commands)

    def __iter__(self) -> Iterator[Command]:
        """按当前层的顺序迭代命令，不展开子列表。"""
        return iter(self._commands)
    def __len__(self) -> int:
        """返回当前层的命令数量，不计子列表。"""
        return len(self._commands)
    def __getitem__(self, index: int | slice) -> Command | list[Command]:
        """按当前层下标或切片读取命令；切片返回普通列表。"""
        return self._commands[index]

    @staticmethod
    def _check(node):
        core.require(isinstance(node, Command), 'Expected a Command object')

    def append(self, node: CommandT) -> CommandT:
        """追加一条命令并返回该对象。

        node -- Command 对象；类型错误时抛出 ValueError，列表保持不变。
        """
        self._check(node)
        self._commands.append(node)
        return node

    def extend(self, nodes: Iterable[Command]) -> None:
        """按顺序追加多条命令。

        nodes -- 命令可迭代对象。全部通过类型检查后追加，返回 None。
        """
        nodes = list(nodes)
        for node in nodes: self._check(node)
        self._commands.extend(nodes)

    def _walk(self, recursive=True, ancestors=()):
        core.require(id(self) not in ancestors, 'Cyclic event list')
        ancestors = (*ancestors, id(self))
        for i, node in enumerate(self._commands):
            yield self, i, node
            if recursive:
                children = [node.then, node.otherwise] if isinstance(node, If) else [node.body] if isinstance(node, Loop) else [body for _,body in node.choices] if isinstance(node, ShowChoices) else []
                for child in children:
                    if child is not None: yield from child._walk(True, ancestors)

    def find(self, command_type: type[CommandT], recursive: bool = True) -> list[CommandT]:
        """按类型返回命令对象列表。

        command_type -- 要查找的 Command 子类，包含其子类实例。
        recursive -- 默认为 True，按深度优先顺序包含嵌套分支和循环；
            False 仅查当前层。

        返回原对象引用，无匹配时返回空列表；循环引用会抛出 ValueError。
        """
        return [node for _, _, node in self._walk(recursive) if isinstance(node, command_type)]

    def _locate(self, node):
        locations = [(parent, i) for parent, i, found in self._walk() if found is node]
        core.require(len(locations) == 1, 'Node must occur exactly once in this event list')
        return locations[0]

    def insert_before(self, anchor: Command, node: Command) -> None:
        """在 anchor 对象前插入 node，返回 None。

        递归定位 anchor；未找到或出现多次、node 不是命令时抛出 ValueError。
        """
        self._check(node); parent, i = self._locate(anchor); parent._commands.insert(i, node)

    def insert_after(self, anchor: Command, node: Command) -> None:
        """在 anchor 对象后插入 node，返回 None。

        递归定位 anchor；未找到或出现多次、node 不是命令时抛出 ValueError。
        """
        self._check(node); parent, i = self._locate(anchor); parent._commands.insert(i + 1, node)

    def replace(self, anchor: Command, node: Command) -> None:
        """用 node 替换 anchor 对象及其子列表，返回 None。

        递归定位 anchor；未找到或出现多次、node 不是命令时抛出 ValueError。
        """
        self._check(node); parent, i = self._locate(anchor); parent._commands[i] = node

    def remove(self, node: Command) -> None:
        """删除 node 对象及其子列表，返回 None。

        递归定位 node；未找到或出现多次时抛出 ValueError。
        """
        parent, i = self._locate(node); del parent._commands[i]

    def to_spec(self) -> list[dict[str, Any]]:
        # Reject cycles before recursive serialization.
        """返回按顺序排列的语义命令字典列表。

        不生成底层指令，不写文件。发现循环引用时抛出 ValueError；
        这里只进行部分参数检查，完整事件校验使用 compile。
        """
        list(self._walk())
        return [{'type': 'raw', 'commands': node._encode_source()}
                if isinstance(node, ShowText) and hasattr(node, '_source_commands')
                else node.to_spec() for node in self._commands]

    def to_document(self) -> dict[str, Any]:
        """返回含 version 和 commands 的语义文档，供 CLI compile 使用。

        不写文件，也不进行完整控制流校验。
        """
        return {'version': 1, 'commands': self.to_spec()}

    def compile(self) -> list[dict[str, Any]]:
        """编译并返回完整的 MZ 事件指令数组。

        新建和读取的列表均按当前嵌套关系生成结构；未知指令块保持内部关系。
        修改文字时保留已有指令的额外字段。参数非法或 BreakLoop
        位于循环外时抛出 ValueError，不写文件也不执行 JavaScript。

        离线使用已核对的编码规则；不检查目标工程版本、数据库引用或
        插件运行行为。工程兼容性由 events.py apply 进一步检查。
        """
        return core.compile_document(self.to_document())

    def to_plan(self, target: dict[str, Any], *, op: EditOperation = 'replace_all',
                index: int | None = None, expect_list_sha256: str | None = None) -> dict[str, Any]:
        """返回供 events.py apply 使用的修改计划，不写工程。

        target -- 公共事件 {"kind": "common", "id": 165}，或地图页
            {"kind": "map", "map_id": 1, "event_id": 3, "page_index": 0}；
            page_index 从 0 开始，其他 ID 从 1 开始。
        op -- 默认 replace_all，替换整段事件；append 表示末尾追加；
            insert_before、insert_after、replace 表示相对已有指令块修改。
        index -- 相对修改必填，使用 inspect 返回的原始指令起始下标。
        expect_list_sha256 -- 相对修改必填，使用 inspect 返回的列表指纹。

        from_commands 读取的列表省略编辑选项，自动生成绑定原始列表指纹的
        replace_all 计划；写入层只改变发生变化的 JSON 区段。

        op、index 和 expect_list_sha256 仅接受关键字参数。
        目标格式或操作参数不合法时抛出 ValueError。片段的控制流由 apply
        结合目标上下文校验，导出计划时不检查工程是否存在或完整参数合法性。
        """
        if hasattr(self, '_source_raw'):
            core.require(op == 'replace_all' and index is None and expect_list_sha256 is None,
                         'Decoded event plans replace the original snapshot; omit edit options')
            self.compile()
            expect_list_sha256 = core.digest(self._source_raw)
        locate(target)
        core.require(op in ('replace_all', 'append', 'insert_before', 'insert_after', 'replace'), 'Unsupported plan operation')
        indexed = op in ('insert_before', 'insert_after', 'replace')
        core.require(indexed == (index is not None), 'index required only for indexed operations')
        core.require(not indexed or expect_list_sha256 is not None, 'Indexed edits require the inspect fingerprint')
        if index is not None: core.integer(index)
        edit = {'target': dict(target), 'op': op, 'commands': self.to_spec()}
        if index is not None: edit['index'] = index
        if expect_list_sha256 is not None: edit['expect_list_sha256'] = expect_list_sha256
        return {'version': 1, 'edits': [edit]}
