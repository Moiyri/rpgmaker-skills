"""System.json 的 Types 设置。"""
from copy import deepcopy
from .backend import db, integer

TYPES = {
    'elements': ('属性', 'elements'),
    'skill_types': ('技能类型', 'skillTypes'),
    'weapon_types': ('武器类型', 'weaponTypes'),
    'armor_types': ('防具类型', 'armorTypes'),
    'equipment_types': ('装备类型', 'equipTypes'),
}


class TypeList:
    """编号名称列表；ID 从 1 开始，0 为保留位。清空不移动后续编号。"""
    def __init__(self, system, key, title):
        self.system, self.key, self.title = system, key, title
        values = self.values
        db.require(isinstance(values, list) and len(values) >= 1 and
                   all(isinstance(v, str) for v in values), 'Expected type name array')
    @property
    def values(self):
        return self.system._data[self.key]
    def get(self, id):
        """按 ID 返回名称。"""
        integer(id, 1, len(self.values) - 1)
        return self.values[id]
    def set(self, id, name):
        """修改已有编号的名称，不修改引用它的编号。"""
        self.get(id)
        db.require(isinstance(name, str), 'Expected name string')
        self.values[id] = name
    def add(self, name):
        """追加名称，返回新 ID；允许重名，不自动复用空槽。"""
        db.require(isinstance(name, str), 'Expected name string')
        self.values.append(name)
        return len(self.values) - 1
    def clear(self, id):
        """将名称清空，保留 ID 和引用；不代表禁用该类型。"""
        self.set(id, '')
    def find(self, text):
        """按名称子串搜索，返回 (ID, 名称) 列表。"""
        db.require(isinstance(text, str), 'Expected search text')
        return [(i, v) for i, v in enumerate(self.values) if i and text.casefold() in v.casefold()]
    def list(self, *, search=None, offset=0, limit=50):
        """返回简短文本，包含未提交修改；空名称与重复名称保留实际编号。"""
        integer(offset); integer(limit, 1)
        rows = self.find('' if search is None else search)
        shown = rows[offset:offset + limit]
        lines = [f'{self.title}（共 {len(rows)} 项）']
        lines.extend(f'{i} {name or "（未命名）"}' for i, name in shown)
        if offset + len(shown) < len(rows):
            lines.append(f'还有更多：offset={offset + len(shown)}')
        return '\n'.join(lines)


class System:
    """工程 Types 设置；与物品、角色共用 preview/commit。"""
    def __init__(self, owner):
        self.owner = owner
        self.raw = db.file_path(owner.root, 'System.json').read_bytes()
        self.original = db.read_document(self.raw)
        db.require(isinstance(self.original, dict), 'Expected System object')
        self._data = deepcopy(self.original)
        self._lists = {}
    def _types(self, name):
        if name not in self._lists:
            title, key = TYPES[name]
            db.require(key in self._data, f'Missing System field: {key}')
            self._lists[name] = TypeList(self, key, title)
        return self._lists[name]
    @property
    def elements(self):return self._types('elements')
    @property
    def skill_types(self):return self._types('skill_types')
    @property
    def weapon_types(self):return self._types('weapon_types')
    @property
    def armor_types(self):return self._types('armor_types')
    @property
    def equipment_types(self):return self._types('equipment_types')
    def prepare(self):
        db.require(db.file_path(self.owner.root, 'System.json').read_bytes() == self.raw,
                   'System.json changed; reload the Database')
        ops = [dict(op='test', file='System.json', path=[], expect=self.original)]
        for key in self._data:
            if self._data.get(key) != self.original.get(key):
                ops.append(dict(op='set', file='System.json', path=[key], value=self._data[key]))
        return ops
