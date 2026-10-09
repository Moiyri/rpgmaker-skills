"""公共事件条目管理；内容编写交给事件技能。"""
from copy import deepcopy
from dataclasses import dataclass
from .backend import db, integer


def blank_event(id):
    return dict(id=id,list=[dict(code=0,indent=0,parameters=[])],name='',switchId=1,trigger=0)


@dataclass(frozen=True)
class CommonEventEntry:
    """只读条目摘要；没有指令列表或可写属性。"""
    id: int
    name: str
    trigger: str
    switch_id: int


class CommonEvents:
    def __init__(self,owner):
        self.owner=owner;self.raw=db.file_path(owner.root,'CommonEvents.json').read_bytes()
        self.original=db.read_document(self.raw)
        db.require(isinstance(self.original,list) and self.original and self.original[0] is None,'Invalid CommonEvents array')
        self._values=deepcopy(self.original)
    def _entry(self,id):
        integer(id,1,len(self._values)-1)
        value=self._values[id]
        db.require(isinstance(value,dict) and value.get('id')==id,'Missing common event')
        return CommonEventEntry(id,value['name'],{0:'none',1:'autorun',2:'parallel'}.get(value['trigger'],str(value['trigger'])),value['switchId'])
    def find(self,text):
        """按名称子串搜索，返回只读条目摘要。"""
        db.require(isinstance(text,str),'Expected name text')
        return [self._entry(i) for i,v in enumerate(self._values) if i and v and text.casefold() in v['name'].casefold()]
    def list(self,*,include_empty=False,offset=0,limit=50):
        """列出 ID、名称和触发方式；默认跳过完全空白的标准条目。"""
        integer(offset);integer(limit,1)
        rows=[e for e in self.find('') if include_empty or not db.equal(self._values[e.id],blank_event(e.id))]
        shown=rows[offset:offset+limit]
        result=[f'公共事件 {len(rows)} 项']+[f'{e.id:03d} {e.name or "（未命名）"} | {e.trigger} | switch={e.switch_id}' for e in shown]
        if offset+len(shown)<len(rows):result.append(f'还有更多：offset={offset+len(shown)}')
        return '\n'.join(result)
    def create(self,name='',id=None):
        """创建空事件，返回含 ID 的只读摘要；省略 ID 追加，指定 ID 只使用空槽。"""
        db.require(isinstance(name,str),'Expected name text')
        target=len(self._values) if id is None else integer(id,1,len(self._values))
        if target<len(self._values):
            db.require(self._values[target] is None or db.equal(self._values[target],blank_event(target)),'Target common event is not empty')
        value=blank_event(target);value['name']=name
        if target==len(self._values):self._values.append(value)
        else:self._values[target]=value
        return self._entry(target)
    def delete(self,id):
        """清空整条公共事件，保留编号；同时移除指令和扩展字段，不修复调用引用。"""
        self._entry(id);self._values[id]=blank_event(id)
    def prepare(self):
        db.require(db.file_path(self.owner.root,'CommonEvents.json').read_bytes()==self.raw,'CommonEvents.json changed; reload')
        ops=[dict(op='test',file='CommonEvents.json',path=[],expect=self.original)]
        for id,value in enumerate(self._values):
            if id<len(self.original):
                if not db.equal(value,self.original[id]):ops.append(dict(op='set',file='CommonEvents.json',path=[id],value=value))
            else:ops.append(dict(op='splice',file='CommonEvents.json',path=[],index=id,delete_count=0,items=[value]))
        return ops
