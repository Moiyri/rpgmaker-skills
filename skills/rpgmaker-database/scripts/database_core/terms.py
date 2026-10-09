"""Terms（用语）：保持数组编号、保留位与消息键。"""
from .backend import db, integer

LABELS = {
    'basic': ['等级','等级缩写','HP','HP缩写','MP','MP缩写','TP','TP缩写','经验','经验缩写'],
    'params': ['最大HP','最大MP','攻击力','防御力','魔法攻击','魔法防御','敏捷','幸运','命中','闪避'],
    'commands': ['战斗','逃跑','攻击','防御','物品','技能','装备菜单','状态','整队','保存','结束游戏','选项','武器','防具','关键物品','更换装备','最强装备','清空装备','新游戏','继续', '保留位','返回标题','取消','保留位','购买','出售'],
}


class TermList:
    """list/find 查询键及文本；get/set/clear 按查询结果的编号或消息键操作。"""
    def __init__(self,store,key):
        self.store,self.key=store,key
        db.require('terms' in store._data and key in store._data['terms'],f'Missing terms.{key}')
    @property
    def _data(self):return self.store._data['terms'][self.key]
    def get(self,key):
        """基本、参数、指令传数组下标；消息传原始键如 saveMessage。"""
        if isinstance(self._data,list):integer(key,0,len(self._data)-1)
        else:db.require(isinstance(key,str) and key in self._data,'Unknown message key')
        return self._data[key]
    def set(self,key,text):
        """修改文本；保留 %1 等替换符和所需控制字符。null 保留位不可修改。"""
        current=self.get(key)
        db.require(isinstance(current,str),'Reserved/non-text term cannot be edited')
        db.require(isinstance(text,str),'Expected text string')
        self._data[key]=text
    def clear(self,key):
        """清空文本为字符串，不删除键、不改变编号。"""
        self.set(key,'')
    def find(self,text):
        """按键、栏目说明或当前文本搜索，返回 (键, 文本) 列表。"""
        db.require(isinstance(text,str),'Expected search text')
        rows=enumerate(self._data) if isinstance(self._data,list) else self._data.items()
        return [(key,value) for key,value in rows if text.casefold() in f'{key} {self._label(key)} {value}'.casefold()]
    def _label(self,key):
        labels=LABELS.get(self.key,[])
        return labels[key] if type(key) is int and key<len(labels) else ''
    def list(self,*,search='',offset=0,limit=60):
        """简短列表，包含下标／键、栏目含义与当前文本；支持搜索分页。"""
        integer(offset);integer(limit,1)
        rows=self.find(search);shown=rows[offset:offset+limit]
        lines=[f'{self.key}（共 {len(rows)} 项）']
        lines.extend(f'{key} {self._label(key)}: {value!r}' for key,value in shown)
        if offset+len(shown)<len(rows):lines.append(f'还有更多：offset={offset+len(shown)}')
        return '\n'.join(lines)


class Terms:
    """编辑器 Terms；货币名称属于 db.system.currency_unit。"""
    def __init__(self,store):self.store=store
    @property
    def basic(self):return TermList(self.store,'basic')
    @property
    def params(self):return TermList(self.store,'params')
    @property
    def commands(self):return TermList(self.store,'commands')
    @property
    def messages(self):return TermList(self.store,'messages')
    def describe(self):return '\n\n'.join(getattr(self,key).list() for key in ['basic','params','commands','messages'])
