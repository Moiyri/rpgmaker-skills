"""数据库会话：快照、预览及正式提交。"""
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from .backend import db
from .items import Items, blank_item


@dataclass(frozen=True)
class Preview:
    """预览凭证，绑定工程、文件快照与修改内容；commit 必须传入原凭证。"""
    fingerprint: str
    summary: str
    def __str__(self):return self.summary


class Database:
    """打开工程并编辑物品。preview() 返回凭证，commit(preview) 通过正式后端提交。

    工程文件或内存修改在预览后变化均拒绝写入。一次会话可修改多个物品。
    提交后创建新 Database 继续编辑；当前会话关闭，旧对象不应复用。
    """
    def __init__(self,project):
        self.root=db.root_path(Path(project)/'data')
        self._raw=db.file_path(self.root,'Items.json').read_bytes()
        self._items=db.read_document(self._raw)
        db.require(isinstance(self._items,list),'Items must be an array')
        self.items=Items(self)
        self._closed=False
        self._actors=None
        self._common_events=None
        self._system=None
        self._maps=None
    @property
    def maps(self):
        """地图目录与属性；事件编写使用事件技能。"""
        if self._maps is None:
            from .maps import Maps
            self._maps=Maps(self)
        return self._maps

    @property
    def types(self):
        """Types（类型）：属性、技能、武器、防具和装备类型。"""
        if self._system is None:
            from .system import System
            self._system=System(self)
        return self._system

    @property
    def system(self):
        """系统设置，与 Types 共享文件和事务。"""
        from .system_settings import SystemSettings
        return SystemSettings(self.types)

    @property
    def switches(self):
        """开关编号与名称；不操作游戏运行状态。"""
        from .switch_variables import NamedSlots
        return NamedSlots(self.types,'switches','开关')

    @property
    def variables(self):
        """变量编号与名称；不操作游戏运行值。"""
        from .switch_variables import NamedSlots
        return NamedSlots(self.types,'variables','变量')

    @property
    def terms(self):
        """Terms（用语）：基本、参数、指令及消息文本。"""
        from .terms import Terms
        return Terms(self.types)

    @property
    def common_events(self):
        """公共事件条目：列表、搜索、创建、删除；指令由事件技能编辑。"""
        if self._common_events is None:
            from .common_events import CommonEvents
            self._common_events=CommonEvents(self)
        return self._common_events

    @property
    def actors(self):
        """按需读取角色数据库。"""
        if self._actors is None:
            from .actors import Actors
            self._actors=Actors(self)
        return self._actors

    def _prepare(self):
        db.require(not self._closed,'Session closed; open a new Database')
        db.require(db.file_path(self.root,'Items.json').read_bytes()==self._raw,'Items.json changed; reload the Database')
        ops=[{'op':'test','file':'Items.json','path':[],'expect':self._items}]
        refs={}
        def reference(file,id):
            if file not in refs:refs[file]=db.file_path(self.root,file).read_bytes()
            data=db.read_document(refs[file])
            db.require(type(id) is int and 0<id<len(data) and isinstance(data[id],dict) and data[id].get('id')==id,f'Missing reference {file}:{id}')
        for id,item in sorted(self.items._cache.items()):
            value=item.to_data()
            original=self._items[id] if id<len(self._items) else None
            old=original if original is not None else blank_item(id)
            if original is not None and db.equal(value,old):continue
            # Validate only changed known fields; preserve existing plugin variants.
            from .items import Item,Damage
            for cls,new,prior in [(Item,item._data,old),(Damage,value['damage'],old['damage'])]:
                for field in vars(cls).values():
                    from .items import Field
                    if isinstance(field,Field) and not db.equal(new.get(field.key),prior.get(field.key)):
                        test=type('Fields',(),{})();test._data={}
                        field.__set__(test,field.choices.get(new[field.key],new[field.key]) if field.choices else new[field.key])
            for effect in value['effects']:
                if any(db.equal(effect,e) for e in old['effects']):continue
                if effect.get('code') in (21,22) and effect.get('dataId')!=0:reference('States.json',effect['dataId'])
                elif effect.get('code')==43:reference('Skills.json',effect['dataId'])
                elif effect.get('code')==44:
                    if self._common_events is not None:self._common_events._entry(effect['dataId'])
                    else:reference('CommonEvents.json',effect['dataId'])
            if value['animationId']!=old['animationId'] and value['animationId']>0:reference('Animations.json',value['animationId'])
            if value['damage']['elementId']!=old['damage']['elementId'] and value['damage']['elementId']>0:
                file='System.json';refs[file]=db.file_path(self.root,file).read_bytes()
                elements=self._system._data['elements'] if self._system is not None else db.read_document(refs[file])['elements']
                db.require(value['damage']['elementId']<len(elements),'Unknown element ID')
            if id<len(self._items):
                ops.append({'op':'set','file':'Items.json','path':[id],'value':value})
            else:
                ops.append({'op':'splice','file':'Items.json','path':[],'index':id,'delete_count':0,'items':[value]})
        if self._actors is not None:
            actor_ops=self._actors.prepare()
            for op in actor_ops[1:]:
                value=op['value'] if op['op']=='set' else op['items'][0]
                prior=self._actors.original[value['id']] if value['id']<len(self._actors.original) else None
                if prior is None or value['classId']!=prior['classId']:
                    reference('Classes.json',value['classId'])
            ops.extend(actor_ops)
        if self._system is not None:
            data=self._system._data;old=self._system.original
            if data.get('partyMembers')!=old.get('partyMembers'):
                for actor_id in data['partyMembers']:
                    if self._actors is not None:
                        self._actors.get(actor_id)
                    else:reference('Actors.json',actor_id)
            for key in [None,'boat','ship','airship']:
                current=data if key is None else data.get(key,{})
                prior=old if key is None else old.get(key,{})
                fields=['startMapId','startX','startY']
                if any(current.get(k)!=prior.get(k) for k in fields):
                    mid=current['startMapId']
                    if mid:
                        file=f'Map{mid:03d}.json'
                        refs[file]=db.file_path(self.root,file).read_bytes()
                        map_data=db.read_document(refs[file])
                        db.require(current['startX']<map_data['width'] and current['startY']<map_data['height'],'Start position outside map')
            ops.extend(self._system.prepare())
        if self._common_events is not None:ops.extend(self._common_events.prepare())
        if self._maps is not None:ops.extend(self._maps.prepare())
        plan={'version':1,'format':'preserve','operations':ops}
        originals,updated,log=db.prepare(self.root,plan)
        for file,raw in refs.items():
            db.require(db.file_path(self.root,file).read_bytes()==raw,'Reference changed during preview')
            if file in originals:
                db.require(originals[file]==raw,'Reference snapshot changed')
            else:
                originals[file]=raw;updated[file]=raw
        result=db.preview_result(self.root,originals,updated,plan)
        changes=[]
        for op in ops[1:]:
            if op['op']=='test':continue
            if op['file'].startswith('Map'):
                changes.append(f'{op["file"]} {op["op"]} {op.get("path", [])}: {str(op.get("value",""))[:300]}')
                continue
            if op['file']=='System.json':
                key=op['path'][0]
                changes.append(f'System.json {key}: {self._system.original[key]!r} → {op["value"]!r}')
                continue
            value=op['value'] if op['op']=='set' else op['items'][0]
            id=value['id']
            table=self._items if op['file']=='Items.json' else self._common_events.original if op['file']=='CommonEvents.json' else self._actors.original
            old=(table[id] if id<len(table) else None) or {}
            changes.append(f'{op["file"]} {id}: {value["name"]}')
            for key,new in value.items():
                if not db.equal(new,old.get(key)):changes.append(f'  {key}: {old.get(key)!r} → {new!r}')
        return originals,updated,Preview(result['preview_sha256'],'\n'.join(changes) or '无修改')
    def preview(self):
        """校验修改字段和新增引用，展示变更并生成提交凭证。"""
        return self._prepare()[2]
    def commit(self,preview):
        """提交已经预览的修改，返回事务备份路径；无修改返回 None。"""
        db.require(isinstance(preview,Preview),'Expected Preview from preview()')
        originals,updated,current=self._prepare()
        db.require(current.fingerprint==preview.fingerprint,'Preview changed; preview again')
        transaction=db.commit(self.root,originals,updated)
        self._closed=True
        return transaction
